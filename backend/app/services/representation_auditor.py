from __future__ import annotations

import hashlib
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cognitive.client import chat_json, chat_json_schema
from app.config import settings
from app.execution_integrity import require_cognition_ready
from app.models.event import RepresentationAuditRun
from app.services.representation_evidence import (
    RepresentationEvidenceBundle,
    build_frame_pair_evidence_bundle,
    stable_digest,
)
from app.services.representation_authority import (
    build_authority_predicate_snapshot,
    predicate_snapshot_digest,
)

REPRESENTATION_AUDITOR_CONTRACT = "representation-auditor-frame-pair-v0.7"
SHADOW_AUTHORITY_POLICY = "shadow-none-v0.1"


class EventIdentityJudgment(BaseModel):
    value: Literal["SAME_EVENT", "DIFFERENT_EVENT", "UNCERTAIN"]
    support_ids: list[str] = Field(default_factory=list)
    conflict_ids: list[str] = Field(default_factory=list)
    rationale: str
    missing_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def decisive_requires_support(self):
        if self.value != "UNCERTAIN" and not self.support_ids:
            raise ValueError(f"{self.value} requires support_ids")
        return self


class ProvenanceDependencyJudgment(BaseModel):
    value: Literal["REPOST", "DERIVED_FROM", "INDEPENDENT", "UNKNOWN"]
    direction: Literal["A_FROM_B", "B_FROM_A", "NOT_APPLICABLE", "UNKNOWN"]
    support_ids: list[str] = Field(default_factory=list)
    conflict_ids: list[str] = Field(default_factory=list)
    rationale: str
    missing_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance_shape(self):
        if self.value != "UNKNOWN" and not self.support_ids:
            raise ValueError(f"{self.value} requires support_ids")
        if self.value in {"REPOST", "DERIVED_FROM"} and self.direction not in {"A_FROM_B", "B_FROM_A"}:
            raise ValueError(f"{self.value} requires directional A_FROM_B or B_FROM_A")
        if self.value == "INDEPENDENT" and self.direction != "NOT_APPLICABLE":
            raise ValueError("INDEPENDENT requires direction=NOT_APPLICABLE")
        if self.value == "UNKNOWN" and self.direction not in {"UNKNOWN", "NOT_APPLICABLE"}:
            raise ValueError("UNKNOWN provenance cannot carry a directional dependency")
        return self


class RelationContextJudgment(BaseModel):
    value: Literal["RELATED", "UNRELATED", "UNCERTAIN"]
    support_ids: list[str] = Field(default_factory=list)
    conflict_ids: list[str] = Field(default_factory=list)
    rationale: str
    missing_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def decisive_requires_support(self):
        if self.value != "UNCERTAIN" and not self.support_ids:
            raise ValueError(f"{self.value} requires support_ids")
        return self


class FramePairAuditResponse(BaseModel):
    event_identity: EventIdentityJudgment
    provenance_dependency: ProvenanceDependencyJudgment
    relation_context: RelationContextJudgment


class RepresentationAuditValidationError(ValueError):
    pass


_SYSTEM = """You are the RAOS Representation Auditor in SHADOW mode.

Your task is to judge three ORTHOGONAL dimensions for two event-evidence frames:
1. event_identity: whether they describe the same underlying occurrence/state transition.
2. provenance_dependency: whether one Source is a repost/derivative of the other, independently reported, or unknown. This dimension is directional for REPOST/DERIVED_FROM.
3. relation_context: whether they are topically/causally related even if they are different events.

Rules:
- These dimensions are semantically irreducible. Never derive one merely from another.
- SAME_EVENT means the same underlying occurrence/state transition, not merely the same topic, actor, product, or company.
- Similar titles/embeddings/text are candidate evidence only. Similarity alone never proves SAME_EVENT.
- CITES proves only an explicit link. It does not by itself prove DERIVED_FROM, SAME_EVENT, ORIGINAL, or INDEPENDENT.
- If CANONICAL_URL_EQUAL is present, the pair may be alternate observations/versions of the same external resource. In V0.1 provenance_dependency must be UNKNOWN for this case unless a distinct-publication provenance relation is explicitly evidenced; do not call the two Source records REPOST or DERIVED_FROM merely because one rendering is fuller.
- Existing RAOS graph/Event projections are evidence only and may be wrong.
- INDEPENDENT requires positive evidence of independent reporting. Absence of a dependency signal is not evidence of independence; use UNKNOWN.
- If the two frames describe materially different actions/transitions, use DIFFERENT_EVENT even if strongly RELATED.
- relation_context=RELATED requires a concrete world relation: the same concrete actor/object/product/system/ongoing episode, an explicit cross-reference, or a direct causal/response/follow-up/update relationship between the event propositions.
- Broad thematic/domain overlap is NOT enough for RELATED. "Both are about AI", "both involve agents", "both are technology news", or similar category-level overlap must be UNRELATED unless a concrete event relation exists.
- SAME_EVENT may also be RELATED because it trivially shares the same concrete occurrence, but RELATED must never be inferred merely from generic semantic similarity.
- Use only evidence_id values present in the bundle. Never invent evidence ids.
- event_identity and relation_context use: value, support_ids, conflict_ids, rationale, missing_evidence.
- provenance_dependency additionally MUST include direction: A_FROM_B means Source/Frame A is derived/reposted from B; B_FROM_A means B is derived/reposted from A; INDEPENDENT uses NOT_APPLICABLE; UNKNOWN uses UNKNOWN or NOT_APPLICABLE.
- Every non-uncertain/non-unknown judgment MUST cite at least one support_ids entry. This is schema-enforced.
- For SAME_EVENT or DIFFERENT_EVENT, normally cite BOTH FRAME_A and FRAME_B because identity is comparative.
- Preserve uncertainty. Do not force a decisive label.
- Do not output any confidence scalar, score, authority decision, merge instruction, or Attention judgment.
"""


def _user_prompt(bundle: RepresentationEvidenceBundle) -> str:
    return (
        "Audit this immutable RepresentationEvidenceBundle. Return only the schema JSON.\n\n"
        + json.dumps(bundle.payload, ensure_ascii=False, sort_keys=True)
    )


def _dimension_rows(response: FramePairAuditResponse):
    return (
        ("event_identity", response.event_identity, {"UNCERTAIN"}),
        ("provenance_dependency", response.provenance_dependency, {"UNKNOWN"}),
        ("relation_context", response.relation_context, {"UNCERTAIN"}),
    )


def _validate_grounding(
    response: FramePairAuditResponse,
    bundle: RepresentationEvidenceBundle,
) -> None:
    allowed = bundle.evidence_ids
    by_id = {
        str(item["evidence_id"]): item
        for item in bundle.payload.get("evidence") or []
        if isinstance(item, dict) and item.get("evidence_id")
    }
    for name, judgment, non_decisive in _dimension_rows(response):
        support = list(judgment.support_ids)
        conflict = list(judgment.conflict_ids)
        invalid = [eid for eid in [*support, *conflict] if eid not in allowed]
        if invalid:
            raise RepresentationAuditValidationError(
                f"{name} referenced unknown evidence ids: {invalid}"
            )
        if judgment.value not in non_decisive and not support:
            raise RepresentationAuditValidationError(
                f"{name}={judgment.value} has no supporting evidence"
            )

    if response.event_identity.value == "SAME_EVENT":
        support = set(response.event_identity.support_ids)
        exact_identity = bool({"CONTENT_HASH_EQUAL", "CANONICAL_URL_EQUAL"} & support)
        both_frames = {"FRAME_A", "FRAME_B"} <= support
        if not (exact_identity or both_frames):
            raise RepresentationAuditValidationError(
                "SAME_EVENT requires both frame evidence or exact identity; similarity/metadata alone is insufficient"
            )

    if response.event_identity.value == "DIFFERENT_EVENT":
        support = set(response.event_identity.support_ids)
        if not {"FRAME_A", "FRAME_B"} <= support:
            raise RepresentationAuditValidationError(
                "DIFFERENT_EVENT requires evidence from both event frames"
            )

    if "CANONICAL_URL_EQUAL" in bundle.evidence_ids and response.provenance_dependency.value != "UNKNOWN":
        explicit_distinct_provenance = any(
            (item.get("kind") == "EXISTING_SOURCE_GRAPH_FACT")
            and ((item.get("data") or {}).get("relationship") in {"REPOSTS", "DERIVED_FROM"})
            and ((item.get("data") or {}).get("detected_by") in {"PARSER", "METADATA", "USER"})
            for item in bundle.payload.get("evidence") or []
            if isinstance(item, dict)
        )
        if not explicit_distinct_provenance:
            raise RepresentationAuditValidationError(
                "same canonical URL is a Source identity/versioning case; provenance_dependency must remain UNKNOWN"
            )

    if response.provenance_dependency.value == "INDEPENDENT":
        positive = [
            eid
            for eid in response.provenance_dependency.support_ids
            if (by_id.get(eid) or {}).get("kind") == "POSITIVE_INDEPENDENCE_EVIDENCE"
        ]
        if not positive:
            raise RepresentationAuditValidationError(
                "INDEPENDENT requires positive independence evidence; absence of dependency evidence is insufficient"
            )


def _identity_key(
    *,
    bundle_digest: str,
    requested_model: str,
    run_tag: str | None,
) -> str:
    return stable_digest(
        {
            "bundle_digest": bundle_digest,
            "contract": REPRESENTATION_AUDITOR_CONTRACT,
            "requested_model": requested_model,
            "run_tag": run_tag or "default",
        }
    )


def _referenced_evidence(
    response: FramePairAuditResponse,
    bundle: RepresentationEvidenceBundle,
    *,
    kind: str,
) -> list[dict]:
    ids: set[str] = set()
    for _name, judgment, _non_decisive in _dimension_rows(response):
        values = (
            judgment.support_ids
            if kind == "support"
            else judgment.conflict_ids
        )
        ids.update(values)
    by_id = {
        str(item["evidence_id"]): item
        for item in bundle.payload.get("evidence") or []
        if isinstance(item, dict) and item.get("evidence_id")
    }
    return [by_id[eid] for eid in sorted(ids) if eid in by_id]


def audit_frame_pair_shadow(
    db: Session,
    frame_a_id: UUID,
    frame_b_id: UUID,
    *,
    chat_fn=chat_json,
    model: str | None = None,
    run_tag: str | None = None,
    candidate_set_digest: str | None = None,
    provider_label: str = "model",
) -> tuple[RepresentationAuditRun, dict]:
    """Run and persist one replayable SHADOW frame-pair judgment.

    This function cannot authorize or mutate Event/EventSource/SourceEdge.
    """
    if frame_a_id == frame_b_id:
        raise ValueError("Frame-pair audit requires two distinct frames")

    execution = require_cognition_ready()
    bundle = build_frame_pair_evidence_bundle(db, frame_a_id, frame_b_id)
    authority_predicates = build_authority_predicate_snapshot(
        bundle,
        execution_context=execution,
    )
    authority_predicates_digest = predicate_snapshot_digest(authority_predicates)
    requested_model = model or settings.llm_model
    identity_key = _identity_key(
        bundle_digest=bundle.digest,
        requested_model=requested_model,
        run_tag=run_tag,
    )
    existing = db.execute(
        select(RepresentationAuditRun).where(
            RepresentationAuditRun.identity_key == identity_key
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, {"reused": True, "bundle": bundle.payload, "bundle_digest": bundle.digest}

    parsed, meta, validation_events = chat_json_schema(
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _user_prompt(bundle)},
        ],
        FramePairAuditResponse,
        chat_fn=chat_fn,
        model=model,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    response = FramePairAuditResponse.model_validate(parsed)
    _validate_grounding(response, bundle)

    judgments = {
        "event_identity": response.event_identity.model_dump(),
        "provenance_dependency": response.provenance_dependency.model_dump(),
        "relation_context": response.relation_context.model_dump(),
    }
    uncertainty = {
        name: list(judgment.missing_evidence)
        for name, judgment, _ in _dimension_rows(response)
        if judgment.missing_evidence
    }
    execution_digest = hashlib.sha256(
        json.dumps(execution, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    row = RepresentationAuditRun(
        identity_key=identity_key,
        workspace_id="local-default",
        origin_device_id=None,
        authority_epoch=0,
        audit_type="FRAME_PAIR",
        subject_type="EVENT_FRAME",
        subject_id=frame_a_id,
        object_type="EVENT_FRAME",
        object_id=frame_b_id,
        input_evidence_digest=bundle.digest,
        input_frame_ids=[str(frame_a_id), str(frame_b_id)],
        evidence_bundle_refs={
            "bundle_version": bundle.payload["bundle_version"],
            "subject": bundle.payload["subject"],
            "object": bundle.payload["object"],
            "candidate_set_digest": candidate_set_digest,
            "authority_predicates": authority_predicates,
            "authority_predicates_digest": authority_predicates_digest,
        },
        auditor_contract_version=REPRESENTATION_AUDITOR_CONTRACT,
        provider=provider_label,
        model=str(meta.get("model") or requested_model),
        judgments=judgments,
        supporting_evidence=_referenced_evidence(response, bundle, kind="support"),
        conflicting_evidence=_referenced_evidence(response, bundle, kind="conflict"),
        uncertainty=uncertainty,
        proposed_transition={},
        authority_policy_version=SHADOW_AUTHORITY_POLICY,
        authority_result="SHADOW_ONLY",
        authorized_by=None,
        execution_context_digest=execution_digest,
    )
    db.add(row)
    db.flush()
    return row, {
        "reused": False,
        "bundle": bundle.payload,
        "bundle_digest": bundle.digest,
        "model_meta": meta,
        "validation_events": validation_events,
    }
