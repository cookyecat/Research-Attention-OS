from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.cognitive.prompts import MATCH_SYSTEM
from app.cognitive.research_aligned_contract import (
    GROUNDING_SYSTEM,
    RELATION_MAPPING_SYSTEM,
    SUPPORT_BINDING_SYSTEM,
    canonical_semantic_units,
)
from app.cognitive.research_aligned_provider import ResearchAlignedCognitiveProvider
from app.enums import Disposition
from app.models.event import EventEvidenceFrame
from app.models.kernel import KernelNode
from app.services.extraction import merge_extractions
from app.services.frame_conditioned_cognition import event_frame_to_extraction
from app.services.scheduler import RuntimeView, get_decision_strategy, route

RUN_VERSION = "phase16b-multi-event-frame-cognition-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase16b_multi_event_frame_cognition_v0_1"


def _meta() -> dict:
    return {
        "latency_ms": 1,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "model": "phase16b-controlled-transport",
    }


def _support(source_id: UUID, pointer: str, excerpt: str) -> dict:
    return {
        "source_id": str(source_id),
        "support_pointer": pointer,
        "support_excerpt": excerpt,
    }


def _frame(source_id: UUID, *, event_key: str, statement: str, pointer: str) -> EventEvidenceFrame:
    unit_id = f"{event_key}:action_change:1"
    return EventEvidenceFrame(
        id=uuid4(),
        identity_key=f"phase16b-{uuid4()}",
        workspace_id="phase16b-controlled",
        source_id=source_id,
        source_snapshot_id=None,
        analysis_run_id=None,
        frame_contract_version="event-evidence-frame-v0.3",
        semantic_input_digest=f"semantic-{uuid4()}",
        frame_payload={
            "event_key": event_key,
            "event_summary": statement,
            "rendered_event_text": statement,
            "audited_semantic_units": [
                {
                    "unit_id": unit_id,
                    "statement": statement,
                    "epistemic_status": "SOURCE_CLAIM",
                    "confidence": "HIGH",
                    "supports": [_support(source_id, pointer, statement)],
                }
            ],
        },
        frame_digest=f"digest-{uuid4()}",
    )


def _belief_node() -> KernelNode:
    statement = (
        "For a small 64x64 bf16 matrix multiplication with bias, computation dominates "
        "runtime rather than kernel preparation and launch overhead."
    )
    return KernelNode(
        id=uuid4(),
        node_type="BELIEF",
        title="Computation dominates runtime.",
        status="ACTIVE",
        payload={"proposition": statement, "importance": 0.9},
        current_version=1,
    )


def _set_provenance(extraction, source_id: UUID):
    extraction.analysis_provenance = {
        **dict(extraction.analysis_provenance or {}),
        "primary_source_id": str(source_id),
        "independent_source_ids": [str(source_id)],
        "secondary_source_ids": [],
    }
    return extraction


def _run_one(extraction, node: KernelNode) -> dict:
    units = canonical_semantic_units(extraction)
    relevant = any("launch overhead dominates runtime" in row["statement"].lower() for row in units)
    support_id = next(
        (
            row["unit_id"]
            for row in units
            if "launch overhead dominates runtime" in row["statement"].lower()
        ),
        None,
    )

    def fake_chat(messages, **_kwargs):
        system = messages[0]["content"]
        if system == MATCH_SYSTEM:
            if relevant:
                return {
                    "matches": [
                        {
                            "kernel_node_id": str(node.id),
                            "relevance_type": "EVIDENCE",
                            "score": 0.99,
                            "reason": "Directly addresses the frozen performance belief.",
                        }
                    ]
                }, _meta()
            return {"matches": []}, _meta()
        if system == RELATION_MAPPING_SYSTEM:
            if relevant:
                return {
                    "effects": [
                        {
                            "operation": "CHALLENGE",
                            "target_kernel_node_id": str(node.id),
                            "reason": "Audited event evidence directly contradicts the belief.",
                        }
                    ]
                }, _meta()
            return {"effects": []}, _meta()
        if system == SUPPORT_BINDING_SYSTEM:
            return {
                "bindings": [
                    {
                        "relation_id": "R001",
                        "support_unit_ids": [support_id],
                        "jurisdiction_anchor_ids": [],
                        "reason": "Exact event-frame support.",
                    }
                ]
            }, _meta()
        if system == GROUNDING_SYSTEM:
            return {
                "items": [
                    {
                        "relation_id": "R001",
                        "grounding_class": "DIRECT",
                        "reason": "The audited event unit directly contradicts the target proposition.",
                    }
                ]
            }, _meta()
        raise AssertionError(f"unexpected system prompt: {system[:80]}")

    provider = ResearchAlignedCognitiveProvider(chat_fn=fake_chat)
    matches = provider.match_kernel(
        extraction,
        [node],
        query_embedding=[],
        node_embeddings=None,
        ranked_ids=None,
    )
    assessment = provider.assess_cognitive_impact(
        "",
        extraction,
        matches,
        independent_source_count=1,
        secondary_report_count=0,
        nodes=[node],
    )
    strategy = get_decision_strategy(
        "pareto-multidelta-cardinal-free-effect-anchored-open-new"
    )
    draft = route(
        assessment.features,
        RuntimeView(),
        assessment=assessment,
        matches=matches,
        decision_strategy=strategy,
    )
    return {
        "semantic_units": units,
        "matches": [
            {
                "node_id": str(match.node_id),
                "relevance_type": match.relevance_type,
                "score": match.score,
            }
            for match in matches
        ],
        "authorized_effects": [effect.as_dict() for effect in assessment.effects],
        "disposition": draft.disposition.value,
        "urgency": draft.urgency,
        "decision_effect": (
            draft.decision_effect.as_dict() if draft.decision_effect is not None else None
        ),
    }


def run() -> dict:
    source_id = uuid4()
    node = _belief_node()
    frame_a = _frame(
        source_id,
        event_key="evt-performance-result",
        statement=(
            "Profiler evidence shows kernel launch overhead dominates runtime for a small "
            "64x64 bf16 matrix multiplication with bias."
        ),
        pointer="PARA 0004",
    )
    frame_b = _frame(
        source_id,
        event_key="evt-memory-challenge-opening",
        statement="Agent Memory Challenge 2026 Cycle 2 opens on September 20.",
        pointer="PARA 0012",
    )

    ext_a = _set_provenance(event_frame_to_extraction(frame_a), source_id)
    ext_b = _set_provenance(event_frame_to_extraction(frame_b), source_id)
    whole = merge_extractions(deepcopy(ext_a), deepcopy(ext_b))
    _set_provenance(whole, source_id)

    a = _run_one(ext_a, node)
    b = _run_one(ext_b, node)
    whole_result = _run_one(whole, node)

    return {
        "run_version": RUN_VERSION,
        "status": "FRAME_CONDITIONED_COGNITION_PROBE_COMPLETE",
        "source_id": str(source_id),
        "kernel_target_id": str(node.id),
        "frames": {
            "A_PERFORMANCE": {
                "frame_id": str(frame_a.id),
                "event_key": frame_a.frame_payload["event_key"],
                **a,
            },
            "B_MEMORY_CHALLENGE": {
                "frame_id": str(frame_b.id),
                "event_key": frame_b.frame_payload["event_key"],
                **b,
            },
        },
        "whole_source": whole_result,
        "diagnostics": {
            "frame_a_engage": a["disposition"] == Disposition.ENGAGE.value,
            "frame_b_drop": b["disposition"] == Disposition.DROP.value,
            "whole_source_engage": whole_result["disposition"] == Disposition.ENGAGE.value,
            "whole_source_masks_irrelevant_event": (
                a["disposition"] == Disposition.ENGAGE.value
                and b["disposition"] == Disposition.DROP.value
                and whole_result["disposition"] == Disposition.ENGAGE.value
            ),
            "frame_unit_sets_disjoint": (
                {row["unit_id"] for row in a["semantic_units"]}
                .isdisjoint({row["unit_id"] for row in b["semantic_units"]})
            ),
        },
        "guardrails": [
            "In-memory only; no DB writes.",
            "No production AttentionPlan/Event mutation.",
            "Frozen ResearchAligned cognition provider and route are reused.",
            "Controlled fake transport replaces external LLM transport only.",
            "Frame evidence uses audited semantic units with explicit support provenance.",
        ],
    }


def main():
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for name, row in report["frames"].items():
        print(
            name,
            "event_key", row["event_key"],
            "units", len(row["semantic_units"]),
            "matches", len(row["matches"]),
            "effects", len(row["authorized_effects"]),
            "disposition", row["disposition"],
        )
    whole = report["whole_source"]
    print(
        "WHOLE_SOURCE",
        "units", len(whole["semantic_units"]),
        "matches", len(whole["matches"]),
        "effects", len(whole["authorized_effects"]),
        "disposition", whole["disposition"],
    )
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
