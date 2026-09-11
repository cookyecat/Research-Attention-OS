from __future__ import annotations

import hashlib, json, subprocess, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from pydantic import Field
from app.cognitive.client import chat_json, chat_json_schema
from app.cognitive.schemas import StrictModel

RUN_VERSION = "phase10d6l4-grounding-capacity-bracketing-v0.1"
REFERENCE = ROOT / "eval/live/phase10d6l4_strong_grounding_reference_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase10d6l4_grounding_capacity_bracketing_v0_1"
CASES = ("D", "X", "N4")
REPEATS = 3
GroundClass = Literal["DIRECT", "PARTIAL", "INSUFFICIENT", "CONTRADICTS_OPERATION"]

SYSTEM_PROMPT = """You are the Grounding stage for Research Attention OS.
Each semantic relation, its target/jurisdiction, and its support evidence are already frozen.
Do not add, remove, retarget, reinterpret, or replace any relation or support binding.
Classify only whether the supplied support licenses the frozen relation at the target scope:
DIRECT = support directly addresses the target/branch at matching scope and supports the operation.
PARTIAL = genuinely relevant and directionally compatible, but only part of the target scope/operation is licensed.
INSUFFICIENT = topical/adjacent, absence-based, jurisdiction-mismatched, or otherwise does not license the relation.
CONTRADICTS_OPERATION = supplied support points in the opposite direction from the frozen operation.
Return exactly one classification for every relation_id and no others. Return JSON only."""

class GroundingItem(StrictModel):
    relation_id: str
    grounding_class: GroundClass
    reason: str = ""

class GroundingResponse(StrictModel):
    items: list[GroundingItem] = Field(default_factory=list)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 60.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )

def prompt_items(items: list[dict]) -> list[dict]:
    out = []
    for item in items:
        out.append({
            "relation_id": item["relation_id"],
            "operation": item["operation"],
            "target_code": item["target_code"],
            "target_proposition": item["target_proposition"],
            "relation_reason": item["relation_reason"],
            "support": item["support_texts"],
            "jurisdiction_anchor_codes": item["jurisdiction_anchor_codes"],
        })
    return out

def build_user_prompt(items: list[dict]) -> str:
    shape = {"items": [{"relation_id": items[0]["relation_id"], "grounding_class": "DIRECT", "reason": ""}]}
    return "Frozen grounding items:\n" + json.dumps(prompt_items(items), ensure_ascii=False) + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False)

def validate_response(parsed: GroundingResponse, items: list[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected = [x["relation_id"] for x in items]
    got = [x.relation_id for x in parsed.items]
    if len(got) != len(set(got)):
        errors.append("DUPLICATE_RELATION_ID")
    if set(got) != set(expected) or len(got) != len(expected):
        errors.append("RELATION_ID_SET_MISMATCH")
    return (not errors), errors

def run_batch(items: list[dict]) -> dict:
    parsed, meta, events = chat_json_schema(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_user_prompt(items)}],
        GroundingResponse, chat_fn=forced_chat, thinking="disabled", timeout=60.0,
    )
    ok, errors = validate_response(parsed, items)
    return {
        "status": "OK" if ok else "INVALID",
        "errors": errors,
        "items": [{"relation_id": x.relation_id, "grounding_class": x.grounding_class, "reason": x.reason} for x in parsed.items],
        "meta": meta,
        "schema_events": events,
    }

def is_critical(strong: str, weak: str) -> bool:
    if strong == "DIRECT" and weak in {"INSUFFICIENT", "CONTRADICTS_OPERATION"}:
        return True
    if strong in {"INSUFFICIENT", "CONTRADICTS_OPERATION"} and weak == "DIRECT":
        return True
    return False

def summarize(reference_items: list[dict], runs_by_case: dict[str, list[dict]]) -> dict:
    strong = {x["relation_id"]: x["strong_class"] for x in reference_items}
    votes: dict[str, Counter] = {rid: Counter() for rid in strong}
    structured_ok = 0
    for runs in runs_by_case.values():
        for run in runs:
            if run.get("status") == "OK":
                structured_ok += 1
            for item in run.get("items", []):
                if item["relation_id"] in votes:
                    votes[item["relation_id"]][item["grounding_class"]] += 1
    per_item = {}
    confusion = Counter()
    exact = 0
    stable = 0
    critical = 0
    for rid, counter in votes.items():
        modal, count = counter.most_common(1)[0] if counter else (None, 0)
        s = strong[rid]
        if count >= 2:
            stable += 1
        if modal == s:
            exact += 1
        if modal is not None:
            confusion[(s, modal)] += 1
            if is_critical(s, modal):
                critical += 1
        per_item[rid] = {
            "strong_class": s,
            "weak_vote_counts": dict(counter),
            "weak_modal_class": modal,
            "weak_modal_count": count,
            "stable_2_of_3": count >= 2,
            "exact_modal_match": modal == s,
            "critical_modal_error": bool(modal and is_critical(s, modal)),
        }
    return {
        "n_calls": len(CASES) * REPEATS,
        "n_structured_ok_calls": structured_ok,
        "structured_success_rate": structured_ok / (len(CASES) * REPEATS),
        "n_items": len(strong),
        "n_stable_items": stable,
        "n_exact_modal_matches": exact,
        "modal_exact_agreement": exact / len(strong),
        "critical_modal_errors": critical,
        "confusion": {f"{a}->{b}": n for (a, b), n in sorted(confusion.items())},
        "per_item": per_item,
    }

def main() -> int:
    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    items = ref["items"]
    if len(items) != 28:
        raise RuntimeError(f"strong reference item-count drift: {len(items)}")
    runs_by_case: dict[str, list[dict]] = {}
    for label in CASES:
        case_items = [x for x in items if x["case"] == label]
        if not case_items:
            raise RuntimeError(f"missing grounding items for {label}")
        runs = []
        for repeat in range(1, REPEATS + 1):
            try:
                run = run_batch(case_items)
            except Exception as exc:
                run = {"status": "ERROR", "errors": [f"{type(exc).__name__}:{str(exc)[:500]}"], "items": []}
            run["repeat"] = repeat
            runs.append(run)
            print(json.dumps({
                "case": label, "repeat": repeat, "status": run["status"],
                "errors": run.get("errors", []), "n_items": len(run.get("items", [])),
            }, ensure_ascii=False), flush=True)
        runs_by_case[label] = runs
    summary = summarize(items, runs_by_case)
    out = {
        "run_version": RUN_VERSION,
        "status": "GROUNDING_CAPACITY_BRACKETING_WEAK_BOUND",
        "measurement_sha": git_head(),
        "strong_reference": str(REFERENCE.relative_to(ROOT)),
        "strong_reference_sha256": sha256(REFERENCE),
        "grounding_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "cases": list(CASES),
        "repeats_per_case": REPEATS,
        "summary": summary,
        "runs_by_case": runs_by_case,
        "guardrails": [
            "Strong-model labels were frozen before any Flash grounding outcome.",
            "Strong labels/rationales are not included in the Flash prompt payload.",
            "Relation, support binding, target and jurisdiction are frozen; Grounding cannot alter them.",
            "Flash is a robustness lower bound, not Grounding truth Gold.",
            "No Attention policy or production switch is evaluated; Phase 9A remains paused.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    compact = {k: v for k, v in summary.items() if k != "per_item"}
    print("SUMMARY=" + json.dumps(compact, ensure_ascii=False, sort_keys=True))
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(path))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
