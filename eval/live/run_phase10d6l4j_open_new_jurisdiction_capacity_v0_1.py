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
from app.services.cognitive_impact import node_proposition
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes

RUN_VERSION = "phase10d6l4j-open-new-jurisdiction-capacity-v0.1"
REFERENCE = ROOT / "eval/live/phase10d6l4_strong_grounding_reference_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase10d6l4j_open_new_jurisdiction_capacity_v0_1"
REPEATS = 3
JurisdictionClass = Literal["SUPPORTED_JURISDICTION", "INSUFFICIENT_JURISDICTION"]
SYSTEM_PROMPT = """You are the OPEN_NEW Jurisdiction Admission stage for Research Attention OS.
The new semantic branch, its support evidence, and its proposed jurisdiction anchors are already frozen.
Do not add, remove, retarget, reinterpret, or replace the branch, support, or anchors.
Judge only whether the supplied Kernel anchors genuinely define a cognitive responsibility area that covers the frozen new branch.
SUPPORTED_JURISDICTION = at least one supplied anchor has semantic scope that legitimately contains the new branch.
INSUFFICIENT_JURISDICTION = anchors are absent, merely broad/topical, or belong to a different research responsibility area.
Broad relevance is not enough. A new branch may be important yet still be outside the current Kernel jurisdiction.
Return exactly one judgment for every relation_id and no others. Return JSON only."""

class JurisdictionItem(StrictModel):
    relation_id: str
    jurisdiction_class: JurisdictionClass
    reason: str = ""

class JurisdictionResponse(StrictModel):
    items: list[JurisdictionItem] = Field(default_factory=list)

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

def load_open_new_items() -> list[dict]:
    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    items = [x for x in ref["items"] if x["operation"] == "OPEN_NEW"]
    if len(items) != 2:
        raise RuntimeError(f"expected exactly 2 frozen OPEN_NEW items, got {len(items)}")
    return items

def kernel_rows() -> dict[str, dict]:
    rows = {}
    for node in build_phase6b_mvp_kernel_nodes():
        rows[str(node.id)] = {
            "id": str(node.id),
            "code": node.metadata.get("fixture_code") if isinstance(node.metadata, dict) else None,
            "type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
        }
    return rows
def prompt_items(items: list[dict]) -> list[dict]:
    nodes = kernel_rows()
    out = []
    for item in items:
        anchors = []
        for idx, anchor_id in enumerate(item["jurisdiction_anchor_ids"]):
            row = dict(nodes.get(anchor_id) or {"id": anchor_id})
            if idx < len(item.get("jurisdiction_anchor_codes") or []):
                row["code"] = item["jurisdiction_anchor_codes"][idx]
            anchors.append(row)
        out.append({
            "relation_id": item["relation_id"],
            "new_branch_reason": item["relation_reason"],
            "support": item["support_texts"],
            "proposed_jurisdiction_anchors": anchors,
        })
    return out

def build_user_prompt(items: list[dict]) -> str:
    shape = {"items": [{
        "relation_id": items[0]["relation_id"],
        "jurisdiction_class": "INSUFFICIENT_JURISDICTION",
        "reason": "",
    }]}
    return (
        "Frozen OPEN_NEW jurisdiction items:\n"
        + json.dumps(prompt_items(items), ensure_ascii=False)
        + "\n\nReturn JSON exactly in this shape:\n"
        + json.dumps(shape, ensure_ascii=False)
    )
def validate_response(parsed: JurisdictionResponse, items: list[dict]) -> tuple[bool, list[str]]:
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
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(items)},
        ],
        JurisdictionResponse,
        chat_fn=forced_chat,
        thinking="disabled",
        timeout=60.0,
    )
    ok, errors = validate_response(parsed, items)
    return {
        "status": "OK" if ok else "INVALID",
        "errors": errors,
        "items": [
            {
                "relation_id": x.relation_id,
                "jurisdiction_class": x.jurisdiction_class,
                "reason": x.reason,
            }
            for x in parsed.items
        ],
        "meta": meta,
        "schema_events": events,
    }
def summarize(items: list[dict], runs: list[dict]) -> dict:
    expected = {x["relation_id"]: "INSUFFICIENT_JURISDICTION" for x in items}
    votes = {rid: Counter() for rid in expected}
    structured_ok = 0
    for run in runs:
        if run.get("status") == "OK":
            structured_ok += 1
        for item in run.get("items", []):
            rid = item["relation_id"]
            if rid in votes:
                votes[rid][item["jurisdiction_class"]] += 1
    per_item = {}
    exact = stable = critical = 0
    for rid, counter in votes.items():
        modal, count = counter.most_common(1)[0] if counter else (None, 0)
        exp = expected[rid]
        stable += count >= 2
        exact += modal == exp
        is_critical = modal == "SUPPORTED_JURISDICTION" and exp == "INSUFFICIENT_JURISDICTION"
        critical += is_critical
        per_item[rid] = {
            "expected_strong_jurisdiction": exp,
            "weak_vote_counts": dict(counter),
            "weak_modal_class": modal,
            "weak_modal_count": count,
            "stable_2_of_3": count >= 2,
            "exact_modal_match": modal == exp,
            "critical_modal_error": is_critical,
        }
    return {
        "n_calls": REPEATS,
        "n_structured_ok_calls": structured_ok,
        "structured_success_rate": structured_ok / REPEATS,
        "n_items": len(items),
        "n_stable_items": stable,
        "n_exact_modal_matches": exact,
        "critical_modal_errors": critical,
        "per_item": per_item,
    }
def main() -> int:
    items = load_open_new_items()
    if any(x["strong_class"] != "INSUFFICIENT" for x in items):
        raise RuntimeError("frozen strong jurisdiction reference drift")
    runs = []
    for repeat in range(1, REPEATS + 1):
        try:
            run = run_batch(items)
        except Exception as exc:
            run = {
                "status": "ERROR",
                "errors": [f"{type(exc).__name__}:{str(exc)[:500]}"],
                "items": [],
            }
        run["repeat"] = repeat
        runs.append(run)
        print(json.dumps({
            "repeat": repeat,
            "status": run["status"],
            "errors": run.get("errors", []),
            "n_items": len(run.get("items", [])),
        }, ensure_ascii=False))

    summary = summarize(items, runs)
    payload = {
        "run_version": RUN_VERSION,
        "status": "OPEN_NEW_JURISDICTION_CAPACITY_BRACKET",
        "measurement_sha": git_head(),
        "strong_reference": str(REFERENCE.relative_to(ROOT)),
        "strong_reference_sha256": sha256(REFERENCE),
        "jurisdiction_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "repeats": REPEATS,
        "summary": summary,
        "runs": runs,
        "guardrails": [
            "relations/support/anchors frozen",
            "full anchor semantics supplied",
            "strong labels hidden from weak prompt",
            "no relation/support/anchor mutation allowed",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / f"phase10d6l4j_open_new_jurisdiction_capacity_v0.1_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = sha256(out)
    print("SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print(f"RESULT_PATH={out.relative_to(ROOT)}")
    print(f"RESULT_SHA256={digest}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
