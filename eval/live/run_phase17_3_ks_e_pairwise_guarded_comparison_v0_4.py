"""Phase17.3-KS-E FULL vs pairwise-guarded KeyBy on frozen Jev v0.7."""
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
    PairwiseAddressUnresolved,
    PropositionFlatMapResultV01,
    SemanticKeyByDraftV01,
    semantic_keyby,
    semantic_keyby_pairwise_guarded,
)
from app.services.event_state_slot_delta import SemanticSlotStateV01

ARTIFACT = ROOT / (
    "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)
SELECTED_ORDINALS = {5, 6, 7, 8}

SEMANTIC_GOLD = {
    5: {
        "P001": ["EXISTING:S006:DISPOSITION"],
        "P002": ["EXISTING:S006:DISPOSITION"],
        "P003": ["EXISTING:S009:QUALITY"],
    },
    6: {
        "P001": ["EXISTING:S006:DISPOSITION"],
        "P002": ["CREATE:QUALITY"],
        "P003": ["CREATE:DISPOSITION"],
    },
    7: {
        "P001": ["CREATE:RELATION"],
        "P002": ["CREATE:STRUCTURE"],
    },
    8: {
        "P001": ["CREATE:RELATION"],
        "P002": ["CREATE:RELATION"],
        "P003": ["EXISTING:S006:FORM"],
        "P004": ["CREATE:DISPOSITION"],
        "P005": ["CREATE:RELATION"],
        "P006": ["EXISTING:S013:QUALITY"],
    },
}

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
                    f"EXISTING:{mutation.existing_slot_key}:"
                    f"{mutation.primitive_family}"
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
        f"{step['observation_key']}|ks-e-pairwise".encode("utf-8")
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


RETRYABLE = (
    ValueError,
    LLMError,
    SchemaValidationError,
    PairwiseAddressUnresolved,
)


def with_retries(call, *, max_attempts=3):
    errors = []
    started = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        try:
            return {
                "value": call(),
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
    return with_retries(lambda: semantic_keyby(
        event_identity=EVENT_IDENTITY,
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=chat_json,
    ))


def run_pairwise(previous, observation, flatmap):
    return with_retries(lambda: semantic_keyby_pairwise_guarded(
        event_identity=EVENT_IDENTITY,
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=chat_json,
        pairwise_chat_fn=chat_json,
        candidate_top_k=2,
        pairwise_repeats=2,
        pairwise_transport="PARALLEL",
        pairwise_max_workers=12,
    ))


def main():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    trajectory = data["trajectory"]
    rows = []

    for index, step in enumerate(trajectory):
        if step["ordinal"] not in SELECTED_ORDINALS:
            continue

        previous = (
            SemanticSlotStateV01.model_validate(
                trajectory[index - 1]["slot_state"]
            )
            if index > 0 else None
        )
        flatmap = PropositionFlatMapResultV01.model_validate(
            step["proposition_flatmap"]
        )
        frozen = SemanticKeyByDraftV01.model_validate(
            step["semantic_keyby"]
        )
        observation = make_observation(data, step, flatmap)

        full = run_full(previous, observation, flatmap)
        guarded = run_pairwise(previous, observation, flatmap)

        base = {
            "ordinal": step["ordinal"],
            "title": step["title"],
            "previous_slot_count": len(previous.slots) if previous else 0,
            "world_proposition_count": len(flatmap.world_propositions),
            "full_attempts": full["attempts"],
            "full_errors": full["errors"],
            "full_latency_s": full["latency_s"],
            "guarded_attempts": guarded["attempts"],
            "guarded_errors": guarded["errors"],
            "guarded_latency_s": guarded["latency_s"],
        }
        if full["value"] is None or guarded["value"] is None:
            row = {
                **base,
                "status": "ERROR",
                "full_success": full["value"] is not None,
                "guarded_success": guarded["value"] is not None,
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            continue
        _full_delta, full_draft = full["value"]
        guarded_result = guarded["value"]

        frozen_sig = action_signature(frozen)
        full_sig = action_signature(full_draft)
        guarded_sig = action_signature(guarded_result.draft)

        pairwise_rows = guarded_result.pairwise_plan.propositions
        row = {
            **base,
            "status": "PASS",
            "candidate_visible_slot_count": (
                guarded_result.candidate_context.visible_slot_count
            ),
            "candidate_compression_ratio": (
                guarded_result.candidate_context.compression_ratio
            ),
            "pairwise_expansion_count": sum(
                item.expansion_triggered for item in pairwise_rows
            ),
            "pairwise_judgment_count": sum(
                len(item.consensus_judgments) for item in pairwise_rows
            ),
            "reuse_authorized_count": len(
                guarded_result.address_policy
                .authorized_existing_slot_key_by_proposition
            ),
            "create_eligible_count": len(
                guarded_result.address_policy
                .create_eligible_proposition_keys
            ),
            "frozen_signature": frozen_sig,
            "full_signature": full_sig,
            "guarded_signature": guarded_sig,
            "semantic_gold_signature": SEMANTIC_GOLD[step["ordinal"]],
            "full_vs_frozen": full_sig == frozen_sig,
            "guarded_vs_full": guarded_sig == full_sig,
            "guarded_vs_frozen": guarded_sig == frozen_sig,
            "frozen_vs_semantic_gold": (
                frozen_sig == SEMANTIC_GOLD[step["ordinal"]]
            ),
            "full_vs_semantic_gold": (
                full_sig == SEMANTIC_GOLD[step["ordinal"]]
            ),
            "guarded_vs_semantic_gold": (
                guarded_sig == SEMANTIC_GOLD[step["ordinal"]]
            ),
            "address_policy": guarded_result.address_policy.model_dump(
                mode="json"
            ),
            "pairwise_plan": guarded_result.pairwise_plan.model_dump(
                mode="json"
            ),
            "full_draft": full_draft.model_dump(mode="json"),
            "guarded_draft": guarded_result.draft.model_dump(mode="json"),
        }
        rows.append(row)
        print(json.dumps({
            key: row[key]
            for key in (
                "ordinal",
                "status",
                "previous_slot_count",
                "candidate_visible_slot_count",
                "candidate_compression_ratio",
                "pairwise_expansion_count",
                "pairwise_judgment_count",
                "reuse_authorized_count",
                "create_eligible_count",
                "full_attempts",
                "guarded_attempts",
                "full_vs_frozen",
                "guarded_vs_full",
                "guarded_vs_frozen",
                "full_latency_s",
                "guarded_latency_s",
            )
        }, ensure_ascii=False), flush=True)
    successful = [row for row in rows if row["status"] == "PASS"]
    result = {
        "benchmark": "phase17.3-ks-e-pairwise-guarded-comparison-v0.4",
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "selected_ordinals": sorted(SELECTED_ORDINALS),
        "case_count": len(rows),
        "successful_case_count": len(successful),
        "error_case_count": len(rows) - len(successful),
        "full_vs_frozen_agreement": (
            sum(row["full_vs_frozen"] for row in successful)
            / len(successful) if successful else None
        ),
        "guarded_vs_full_agreement": (
            sum(row["guarded_vs_full"] for row in successful)
            / len(successful) if successful else None
        ),
        "guarded_vs_frozen_agreement": (
            sum(row["guarded_vs_frozen"] for row in successful)
            / len(successful) if successful else None
        ),
        "frozen_vs_semantic_gold_accuracy": (
            sum(row["frozen_vs_semantic_gold"] for row in successful)
            / len(successful) if successful else None
        ),
        "full_vs_semantic_gold_accuracy": (
            sum(row["full_vs_semantic_gold"] for row in successful)
            / len(successful) if successful else None
        ),
        "guarded_vs_semantic_gold_accuracy": (
            sum(row["guarded_vs_semantic_gold"] for row in successful)
            / len(successful) if successful else None
        ),
        "mean_candidate_compression_ratio": (
            sum(
                row["candidate_compression_ratio"]
                for row in successful
            ) / len(successful)
            if successful else None
        ),
        "pairwise_expansion_count": sum(
            row["pairwise_expansion_count"] for row in successful
        ),
        "pairwise_judgment_count": sum(
            row["pairwise_judgment_count"] for row in successful
        ),
        "mean_full_latency_s": (
            sum(row["full_latency_s"] for row in successful)
            / len(successful) if successful else None
        ),
        "mean_guarded_latency_s": (
            sum(row["guarded_latency_s"] for row in successful)
            / len(successful) if successful else None
        ),
        "rows": rows,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_pairwise_guarded_comparison_v0_4"
        / "phase17_3_ks_e_pairwise_guarded_comparison_v0_4.json"
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
        "full_vs_frozen_agreement": result["full_vs_frozen_agreement"],
        "guarded_vs_full_agreement": result["guarded_vs_full_agreement"],
        "guarded_vs_frozen_agreement": result["guarded_vs_frozen_agreement"],
        "frozen_vs_semantic_gold_accuracy": result["frozen_vs_semantic_gold_accuracy"],
        "full_vs_semantic_gold_accuracy": result["full_vs_semantic_gold_accuracy"],
        "guarded_vs_semantic_gold_accuracy": result["guarded_vs_semantic_gold_accuracy"],
        "mean_candidate_compression_ratio": round(
            result["mean_candidate_compression_ratio"], 4
        ) if result["mean_candidate_compression_ratio"] is not None else None,
        "pairwise_expansion_count": result["pairwise_expansion_count"],
        "pairwise_judgment_count": result["pairwise_judgment_count"],
        "mean_full_latency_s": round(
            result["mean_full_latency_s"], 3
        ) if result["mean_full_latency_s"] is not None else None,
        "mean_guarded_latency_s": round(
            result["mean_guarded_latency_s"], 3
        ) if result["mean_guarded_latency_s"] is not None else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
