from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import math
from typing import Iterable
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.event import EventEvidenceFrame, RepresentationAuditRun
from app.services.representation_auditor import REPRESENTATION_AUDITOR_CONTRACT

REPRESENTATION_BELIEF_VIEW_CONTRACT = "representation-belief-view-v0.1"
PRIOR_IGNORANCE_WEIGHT = 2.0
BASE_RATE_SAME = 0.5
_EVENT_IDENTITY_LABELS = ("SAME_EVENT", "DIFFERENT_EVENT", "UNCERTAIN")


def _normalized_distribution(counts: dict[str, int]) -> dict[str, float]:
    total = sum(max(0, int(counts.get(label, 0))) for label in _EVENT_IDENTITY_LABELS)
    if total <= 0:
        return {label: 0.0 for label in _EVENT_IDENTITY_LABELS}
    return {
        label: max(0, int(counts.get(label, 0))) / total
        for label in _EVENT_IDENTITY_LABELS
    }


def _entropy_bits(distribution: dict[str, float]) -> float:
    value = 0.0
    for label in _EVENT_IDENTITY_LABELS:
        p = float(distribution.get(label, 0.0))
        if p > 0.0:
            value -= p * math.log2(p)
    return value


def _jsd_bits(a: dict[str, float], b: dict[str, float]) -> float:
    midpoint = {
        label: 0.5 * (float(a.get(label, 0.0)) + float(b.get(label, 0.0)))
        for label in _EVENT_IDENTITY_LABELS
    }

    def kl(p: dict[str, float], q: dict[str, float]) -> float:
        out = 0.0
        for label in _EVENT_IDENTITY_LABELS:
            px = float(p.get(label, 0.0))
            qx = float(q.get(label, 0.0))
            if px > 0.0 and qx > 0.0:
                out += px * math.log2(px / qx)
        return out

    return 0.5 * kl(a, midpoint) + 0.5 * kl(b, midpoint)


def _operational_opinion(
    counts: dict[str, int],
    *,
    prior_ignorance_weight: float = PRIOR_IGNORANCE_WEIGHT,
    base_rate_same: float = BASE_RATE_SAME,
) -> dict:
    n_same = max(0, int(counts.get("SAME_EVENT", 0)))
    n_different = max(0, int(counts.get("DIFFERENT_EVENT", 0)))
    n_uncertain = max(0, int(counts.get("UNCERTAIN", 0)))
    sample_count = n_same + n_different + n_uncertain
    denominator = sample_count + float(prior_ignorance_weight)
    if denominator <= 0:
        belief = 0.0
        disbelief = 0.0
        uncertainty = 1.0
    else:
        belief = n_same / denominator
        disbelief = n_different / denominator
        uncertainty = (n_uncertain + float(prior_ignorance_weight)) / denominator
    projected_same = belief + float(base_rate_same) * uncertainty
    return {
        "belief_same_mass": round(belief, 6),
        "disbelief_same_mass": round(disbelief, 6),
        "uncertainty_mass": round(uncertainty, 6),
        "base_rate_same": float(base_rate_same),
        "prior_ignorance_weight": float(prior_ignorance_weight),
        "projected_same_probability_proxy": round(projected_same, 6),
        "calibrated_world_truth_probability": False,
    }


def _pair_key(subject_id: UUID, object_id: UUID) -> tuple[str, str]:
    a, b = str(subject_id), str(object_id)
    return tuple(sorted((a, b)))


def _epoch_key(row: RepresentationAuditRun) -> tuple[str, str, str, str]:
    return (
        str(row.input_evidence_digest),
        str(row.auditor_contract_version),
        str(row.provider or ""),
        str(row.model or ""),
    )


def _epoch_view(rows: list[RepresentationAuditRun]) -> dict:
    if not rows:
        raise ValueError("epoch requires at least one RepresentationAuditRun")
    ordered = sorted(rows, key=lambda row: (row.created_at or datetime.min, str(row.id)))
    counts = Counter()
    for row in ordered:
        value = str((row.judgments.get("event_identity") or {}).get("value") or "UNCERTAIN")
        counts[value if value in _EVENT_IDENTITY_LABELS else "UNCERTAIN"] += 1
    count_payload = {label: int(counts.get(label, 0)) for label in _EVENT_IDENTITY_LABELS}
    response = _normalized_distribution(count_payload)
    opinion = _operational_opinion(count_payload)
    return {
        "input_evidence_digest": ordered[0].input_evidence_digest,
        "auditor_contract_version": ordered[0].auditor_contract_version,
        "provider": ordered[0].provider,
        "model": ordered[0].model,
        "sample_count": len(ordered),
        "iid_sampling_certified": False,
        "effective_sample_count_estimated": False,
        "audit_run_ids": [str(row.id) for row in ordered],
        "first_at": ordered[0].created_at.isoformat() if ordered[0].created_at else None,
        "last_at": ordered[-1].created_at.isoformat() if ordered[-1].created_at else None,
        "counts": count_payload,
        "response_distribution": {
            label: round(float(response[label]), 6) for label in _EVENT_IDENTITY_LABELS
        },
        "response_entropy_bits": round(_entropy_bits(response), 6),
        "decisive_fraction": round(
            (count_payload["SAME_EVENT"] + count_payload["DIFFERENT_EVENT"]) / max(1, len(ordered)),
            6,
        ),
        "operational_opinion": opinion,
        "semantics": {
            "response_distribution": "empirical Auditor response spectrum under frozen evidence/configuration",
            "operational_opinion": "uncertainty-bearing engineering proxy; not calibrated world-truth probability",
        },
    }


def belief_history_from_audits(rows: Iterable[RepresentationAuditRun]) -> dict:
    rows = list(rows)
    if not rows:
        return {
            "belief_contract": REPRESENTATION_BELIEF_VIEW_CONTRACT,
            "epoch_count": 0,
            "epochs": [],
        }

    pair_keys = {_pair_key(row.subject_id, row.object_id) for row in rows}
    if len(pair_keys) != 1:
        raise ValueError("belief history must contain exactly one unordered frame pair")

    grouped: dict[tuple[str, str, str, str], list[RepresentationAuditRun]] = defaultdict(list)
    for row in rows:
        grouped[_epoch_key(row)].append(row)

    epochs = [_epoch_view(group) for group in grouped.values()]
    epochs.sort(key=lambda e: ((e.get("first_at") or ""), e["input_evidence_digest"]))

    previous_by_stream: dict[tuple[str, str, str], dict] = {}
    for epoch in epochs:
        stream = (
            str(epoch["auditor_contract_version"]),
            str(epoch.get("provider") or ""),
            str(epoch.get("model") or ""),
        )
        previous = previous_by_stream.get(stream)
        if previous is None:
            epoch["jsd_from_previous_compatible_epoch_bits"] = None
        else:
            epoch["jsd_from_previous_compatible_epoch_bits"] = round(
                _jsd_bits(
                    previous["response_distribution"],
                    epoch["response_distribution"],
                ),
                6,
            )
        previous_by_stream[stream] = epoch

    pair = sorted(pair_keys)[0]
    latest = epochs[-1]
    return {
        "belief_contract": REPRESENTATION_BELIEF_VIEW_CONTRACT,
        "hypothesis": {
            "type": "SAME_WORLD_EVENT",
            "frame_id_a": pair[0],
            "frame_id_b": pair[1],
        },
        "epoch_count": len(epochs),
        "latest_epoch": latest,
        "epochs": epochs,
        "mutates_graph": False,
        "topology_commitment_authority": "NONE",
        "calibrated_world_truth_probability": False,
    }


def frame_pair_belief_history(
    db: Session,
    frame_a_id: UUID,
    frame_b_id: UUID,
    *,
    auditor_contract: str | None = REPRESENTATION_AUDITOR_CONTRACT,
) -> dict:
    clauses = [
        RepresentationAuditRun.audit_type == "FRAME_PAIR",
        or_(
            (
                (RepresentationAuditRun.subject_id == frame_a_id)
                & (RepresentationAuditRun.object_id == frame_b_id)
            ),
            (
                (RepresentationAuditRun.subject_id == frame_b_id)
                & (RepresentationAuditRun.object_id == frame_a_id)
            ),
        ),
    ]
    if auditor_contract:
        clauses.append(RepresentationAuditRun.auditor_contract_version == auditor_contract)
    rows = db.execute(
        select(RepresentationAuditRun)
        .where(*clauses)
        .order_by(RepresentationAuditRun.created_at.asc(), RepresentationAuditRun.id.asc())
    ).scalars().all()
    return belief_history_from_audits(rows)


def source_representation_beliefs(
    db: Session,
    source_id: UUID,
    *,
    source_ids: Iterable[UUID] | None = None,
    auditor_contract: str | None = REPRESENTATION_AUDITOR_CONTRACT,
    limit: int = 100,
) -> dict:
    version_ids = tuple(source_ids or (source_id,))
    frame_ids = list(
        db.execute(
            select(EventEvidenceFrame.id).where(EventEvidenceFrame.source_id.in_(version_ids))
        ).scalars().all()
    )
    if not frame_ids:
        return {
            "source_id": str(source_id),
            "source_version_ids": [str(value) for value in version_ids],
            "belief_contract": REPRESENTATION_BELIEF_VIEW_CONTRACT,
            "pair_count": 0,
            "returned_pair_count": 0,
            "beliefs": [],
        }

    clauses = [
        RepresentationAuditRun.audit_type == "FRAME_PAIR",
        or_(
            RepresentationAuditRun.subject_id.in_(frame_ids),
            RepresentationAuditRun.object_id.in_(frame_ids),
        ),
    ]
    if auditor_contract:
        clauses.append(RepresentationAuditRun.auditor_contract_version == auditor_contract)

    # Correctness rule: never truncate realizations before building a spectrum.
    # The limit applies to returned hypothesis pairs only. Truncating audit rows
    # here would silently distort counts/probabilities while returning plausible JSON.
    rows = db.execute(
        select(RepresentationAuditRun)
        .where(*clauses)
        .order_by(RepresentationAuditRun.created_at.desc(), RepresentationAuditRun.id.desc())
    ).scalars().all()

    by_pair: dict[tuple[str, str], list[RepresentationAuditRun]] = defaultdict(list)
    for row in rows:
        by_pair[_pair_key(row.subject_id, row.object_id)].append(row)

    beliefs = [belief_history_from_audits(group) for group in by_pair.values()]
    beliefs.sort(
        key=lambda item: (
            str((item.get("latest_epoch") or {}).get("last_at") or ""),
            item["hypothesis"]["frame_id_a"],
            item["hypothesis"]["frame_id_b"],
        ),
        reverse=True,
    )
    pair_limit = max(1, min(int(limit), 500))
    returned = beliefs[:pair_limit]
    return {
        "source_id": str(source_id),
        "source_version_ids": [str(value) for value in version_ids],
        "belief_contract": REPRESENTATION_BELIEF_VIEW_CONTRACT,
        "pair_count": len(beliefs),
        "returned_pair_count": len(returned),
        "beliefs": returned,
    }
