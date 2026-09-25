"""Phase17.3-KS-E live FULL vs CONSTRAINED comparison on frozen Jev v0.7 inputs."""
from pathlib import Path
import hashlib
import json
import sys
import time
from uuid import UUID

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.cognitive.client import LLMError, SchemaValidationError, chat_json
from app.services.event_observation import EventObservationV01
from app.services.event_state_proposition_keyby import (
    PropositionFlatMapResultV01,
    SemanticKeyByDraftV01,
    semantic_keyby,
    semantic_keyby_candidate_aware,
)
from app.services.event_state_slot_delta import SemanticSlotStateV01

ARTIFACT = ROOT / (
    "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)
SELECTED_ORDINALS = {5, 6, 7, 8}

EVENT_IDENTITY = {
    "title": "Jev model launch / emergence and early validation episode",
    "event_type": "MODEL_LAUNCH_EARLY_VALIDATION",
    "actors": ["TypeSafe AI / Jev authors and ecosystem participants"],
    "action": "launch, explain, test, and early-validate Jev",
    "object": "Jev model",
    "time_context": "2026-09-16 through 2026-09-20 emergence episode",
}
def action_signature(draft: SemanticKeyByDraftV01):
    signature = {}
    for route in draft.proposition_routes:
        if route.disposition == "NO_WORLD_VALUE_CHANGE":
            signature[route.proposition_key] = ["NO_CHANGE"]
            continue
        actions = []
        for index in route.mutation_indices:
            mutation = draft.mutations[index]
            if mutation.target == "EXISTING":
                actions.append(
                    f"EXISTING:{mutation.existing_slot_key}:{mutation.primitive_family}"
                )
            else:
                actions.append(f"CREATE:{mutation.primitive_family}")
        signature[route.proposition_key] = sorted(actions)
    return signature


def make_observation(data, step, flatmap):
    refs = sorted({
        ref
        for proposition in flatmap.world_propositions
        for ref in proposition.support_refs
    })
    provenance = hashlib.sha256(
        f"{step['observation_key']}|ks-e-live".encode("utf-8")
    ).hexdigest()
    return EventObservationV01(
        event_id=UUID(data["benchmark_event_id"]),
        observation_key=step["observation_key"],
        source_id=UUID(step["source_id"]),
        evidence_time=step["evidence_time"],
        ingest_time=step["evidence_time"],
        provenance_digest=provenance,
        audited_semantic_unit_refs=tuple(refs),
    )


RETRYABLE = (ValueError, LLMError, SchemaValidationError)


def _with_retries(call, *, max_attempts=3):
    errors = []
    started = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        try:
            value = call()
            return {
                "value": value,
                "attempts": attempt,
                "errors": errors,
                "latency_s": time.perf_counter() - started,
            }
        except RETRYABLE as exc:
            errors.append({
                "attempt": attempt,
                "type": type(exc).__name__,
                "message": str(exc),
            })
    return {
        "value": None,
        "attempts": max_attempts,
        "errors": errors,
        "latency_s": time.perf_counter() - started,
    }


def run_full(previous, observation, flatmap):
    return _with_retries(lambda: semantic_keyby(
        event_identity=EVENT_IDENTITY,
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=chat_json,
    ))


def run_constrained(previous, observation, flatmap):
    return _with_retries(lambda: semantic_keyby_candidate_aware(
        event_identity=EVENT_IDENTITY,
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=chat_json,
        mode="CONSTRAINED",
        candidate_top_k=2,
    ))
def main():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    trajectory = data["trajectory"]
    rows = []

    for index, step in enumerate(trajectory):
        ordinal = step["ordinal"]
        if ordinal not in SELECTED_ORDINALS:
            continue

        previous = (
            SemanticSlotStateV01.model_validate(
                trajectory[index - 1]["slot_state"]
            )
            if index > 0
            else None
        )
        flatmap = PropositionFlatMapResultV01.model_validate(
            step["proposition_flatmap"]
        )
        frozen = SemanticKeyByDraftV01.model_validate(
            step["semantic_keyby"]
        )
        observation = make_observation(data, step, flatmap)

        full_run = run_full(
            previous,
            observation,
            flatmap,
        )
        constrained_run = run_constrained(
            previous,
            observation,
            flatmap,
        )

        base_row = {
            "ordinal": ordinal,
            "title": step["title"],
            "previous_slot_count": len(previous.slots) if previous else 0,
            "world_proposition_count": len(flatmap.world_propositions),
            "full_attempts": full_run["attempts"],
            "full_errors": full_run["errors"],
            "full_latency_s": full_run["latency_s"],
            "constrained_attempts": constrained_run["attempts"],
            "constrained_errors": constrained_run["errors"],
            "constrained_latency_s": constrained_run["latency_s"],
        }
        if full_run["value"] is None or constrained_run["value"] is None:
            row = {
                **base_row,
                "status": "ERROR",
                "full_success": full_run["value"] is not None,
                "constrained_success": constrained_run["value"] is not None,
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            continue

        _full_delta, full_draft = full_run["value"]
        constrained = constrained_run["value"]

        frozen_sig = action_signature(frozen)
        full_sig = action_signature(full_draft)
        constrained_sig = action_signature(constrained.draft)

        row = {
            **base_row,
            "status": "PASS",
            "initial_visible_slot_count": (
                constrained.initial_context.visible_slot_count
            ),
            "final_visible_slot_count": (
                constrained.final_context.visible_slot_count
            ),
            "initial_compression_ratio": (
                constrained.initial_context.compression_ratio
            ),
            "final_compression_ratio": (
                constrained.final_context.compression_ratio
            ),
            "expansion_triggered": constrained.expansion_triggered,
            "expanded_proposition_keys": list(
                constrained.expanded_proposition_keys
            ),
            "frozen_signature": frozen_sig,
            "full_signature": full_sig,
            "constrained_signature": constrained_sig,
            "full_vs_frozen": full_sig == frozen_sig,
            "constrained_vs_full": constrained_sig == full_sig,
            "constrained_vs_frozen": constrained_sig == frozen_sig,
            "full_draft": full_draft.model_dump(mode="json"),
            "constrained_draft": constrained.draft.model_dump(mode="json"),
        }
        rows.append(row)
        print(json.dumps({
            key: row[key]
            for key in (
                "ordinal",
                "status",
                "previous_slot_count",
                "initial_visible_slot_count",
                "final_visible_slot_count",
                "expansion_triggered",
                "expanded_proposition_keys",
                "full_attempts",
                "constrained_attempts",
                "full_vs_frozen",
                "constrained_vs_full",
                "constrained_vs_frozen",
                "full_latency_s",
                "constrained_latency_s",
            )
        }, ensure_ascii=False), flush=True)
    successful = [row for row in rows if row["status"] == "PASS"]
    result = {
        "benchmark": "phase17.3-ks-e-live-constrained-comparison-v0.1",
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "selected_ordinals": sorted(SELECTED_ORDINALS),
        "case_count": len(rows),
        "successful_case_count": len(successful),
        "error_case_count": len(rows) - len(successful),
        "full_retry_count": sum(
            max(0, row["full_attempts"] - 1) for row in rows
        ),
        "constrained_retry_count": sum(
            max(0, row["constrained_attempts"] - 1) for row in rows
        ),
        "constrained_vs_full_agreement": (
            sum(row["constrained_vs_full"] for row in successful)
            / len(successful)
            if successful else None
        ),
        "full_vs_frozen_agreement": (
            sum(row["full_vs_frozen"] for row in successful)
            / len(successful)
            if successful else None
        ),
        "constrained_vs_frozen_agreement": (
            sum(row["constrained_vs_frozen"] for row in successful)
            / len(successful)
            if successful else None
        ),
        "expansion_case_count": sum(
            row["expansion_triggered"] for row in successful
        ),
        "mean_initial_compression_ratio": (
            sum(row["initial_compression_ratio"] for row in successful)
            / len(successful)
            if successful else None
        ),
        "mean_full_latency_s": (
            sum(row["full_latency_s"] for row in successful)
            / len(successful)
            if successful else None
        ),
        "mean_constrained_latency_s": (
            sum(row["constrained_latency_s"] for row in successful)
            / len(successful)
            if successful else None
        ),
        "rows": rows,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_live_constrained_comparison_v0_1"
        / "phase17_3_ks_e_live_constrained_comparison_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "benchmark": result["benchmark"],
        "case_count": result["case_count"],
        "successful_case_count": result["successful_case_count"],
        "error_case_count": result["error_case_count"],
        "full_retry_count": result["full_retry_count"],
        "constrained_retry_count": result["constrained_retry_count"],
        "constrained_vs_full_agreement": result[
            "constrained_vs_full_agreement"
        ],
        "full_vs_frozen_agreement": result[
            "full_vs_frozen_agreement"
        ],
        "constrained_vs_frozen_agreement": result[
            "constrained_vs_frozen_agreement"
        ],
        "expansion_case_count": result["expansion_case_count"],
        "mean_initial_compression_ratio": round(
            result["mean_initial_compression_ratio"], 4
        ),
        "mean_full_latency_s": round(result["mean_full_latency_s"], 3),
        "mean_constrained_latency_s": round(
            result["mean_constrained_latency_s"], 3
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
