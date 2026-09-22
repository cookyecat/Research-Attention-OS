from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import UUID, NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

import app.models  # noqa: F401
from app.cognitive.client import chat_json
from app.db import Base, SessionLocal
from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source, SourceEdge
from app.services.event_observation import (
    EventObservationV01,
    observation_key_for,
)
from app.services.event_state_slot_delta import (
    SLOT_APPLIER_CONTRACT,
    SLOT_DELTA_CONTRACT,
    SLOT_STATE_CONTRACT,
    SlotDeltaV01,
    SemanticSlotStateV01,
    apply_slot_delta,
)
from app.services.event_state_proposition_keyby import (
    PROPOSITION_FLATMAP_CONTRACT,
    SEMANTIC_KEYBY_CONTRACT,
    TWO_STAGE_DECIDER_CONTRACT,
    decide_slot_delta_two_stage,
)
from app.services.source_graph import (
    INDEPENDENCE_RELATIONSHIPS,
    freeze_analysis_relational_context,
)

RUN_VERSION = "phase17-jev-proposition-keyby-replay-v0.1"
PROJECTION_DIR = ROOT / "eval/live/results/phase17_jev_event_gold_projection_v0_2"
FIXTURE = ROOT / "eval/live/fixtures/phase17_jev_longitudinal_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase17_jev_proposition_keyby_replay_v0_1"
DEFAULT_CHECKPOINT = OUT_DIR / "phase17_jev_proposition_keyby_replay_v0.1_checkpoint.json"
BENCHMARK_EVENT_ID = uuid5(NAMESPACE_URL, "raos:benchmark:jev-longitudinal-v0.1")


def _stable_digest(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _delta_label(delta: SlotDeltaV01 | None) -> str:
    if delta is None:
        return "NONE"
    modes = sorted({mutation.mode for mutation in delta.mutations})
    return "+".join(modes)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def _checkpoint_identity(
    *,
    projection_path: Path,
    projection_digest: str,
    items_requested: int,
) -> dict:
    return {
        "run_version": RUN_VERSION,
        "projection_artifact": str(projection_path.relative_to(ROOT)),
        "projection_digest": projection_digest,
        "decider_contract": TWO_STAGE_DECIDER_CONTRACT,
        "flatmap_contract": PROPOSITION_FLATMAP_CONTRACT,
        "keyby_contract": SEMANTIC_KEYBY_CONTRACT,
        "slot_delta_contract": SLOT_DELTA_CONTRACT,
        "slot_state_contract": SLOT_STATE_CONTRACT,
        "applier_contract": SLOT_APPLIER_CONTRACT,
        "execution_contract": "persisted-slot-delta-apply-v0.1",
        "items_requested": items_requested,
    }


def _validate_checkpoint_identity(
    checkpoint: dict,
    *,
    projection_path: Path,
    projection_digest: str,
    items_requested: int,
) -> None:
    expected = _checkpoint_identity(
        projection_path=projection_path,
        projection_digest=projection_digest,
        items_requested=items_requested,
    )
    # items_requested is run horizon metadata, not semantic identity.
    # A shorter verified checkpoint may safely extend to a longer frozen trace;
    # every persisted prefix row is still revalidated by source_id,
    # observation_key, and both fact/event state digests before any new Decide call.
    identity_keys = tuple(
        key for key in expected
        if key != "items_requested"
    )
    mismatches = {
        key: {"checkpoint": checkpoint.get(key), "expected": expected[key]}
        for key in identity_keys
        if checkpoint.get(key) != expected[key]
    }
    if mismatches:
        raise RuntimeError(
            "Checkpoint identity mismatch; refusing cross-contract/projection resume: "
            + json.dumps(mismatches, ensure_ascii=False, sort_keys=True)
        )


def _write_checkpoint(
    *,
    checkpoint_path: Path,
    projection_path: Path,
    projection_digest: str,
    items_requested: int,
    trajectory: list[dict],
    status: str = "IN_PROGRESS",
) -> None:
    payload = {
        **_checkpoint_identity(
            projection_path=projection_path,
            projection_digest=projection_digest,
            items_requested=items_requested,
        ),
        "status": status,
        "completed_observations": len(trajectory),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "trajectory": trajectory,
    }
    _write_json_atomic(checkpoint_path, payload)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_full_projection() -> Path:
    rows = sorted(PROJECTION_DIR.glob("*_full_*.json"))
    if not rows:
        raise RuntimeError(
            "No full Jev Event-Gold projection artifact found. "
            "Run run_phase17_jev_event_gold_projection_v0_2.py first."
        )
    return rows[-1]


def _clone_source(row: Source) -> Source:
    return Source(
        id=row.id,
        source_type=row.source_type,
        title=row.title,
        canonical_url=row.canonical_url,
        content_text=row.content_text,
        published_at=row.published_at,
        publisher=row.publisher,
        language=row.language,
        fingerprint=row.fingerprint,
        content_hash=row.content_hash,
        ingestion_method=row.ingestion_method,
        raw_metadata=dict(row.raw_metadata or {}),
        deleted_at=row.deleted_at,
    )


def _load_source_graph(
    projection: dict,
) -> tuple[dict[UUID, dict], list[Source], list[SourceEdge]]:
    selected_rows = [
        row for row in projection["items"]
        if row.get("status") == "OK" and row.get("source_id")
    ]
    selected_ids = {UUID(row["source_id"]) for row in selected_rows}

    canonical = SessionLocal()
    try:
        edges = (
            canonical.execute(
                select(SourceEdge).where(
                    SourceEdge.source_id.in_(selected_ids),
                    SourceEdge.relationship.in_(list(INDEPENDENCE_RELATIONSHIPS)),
                )
            )
            .scalars()
            .all()
        )
        required_ids = set(selected_ids)
        required_ids.update(edge.target_id for edge in edges)

        source_rows = (
            canonical.execute(select(Source).where(Source.id.in_(required_ids)))
            .scalars()
            .all()
        )
        clones = [_clone_source(row) for row in source_rows]
        edge_clones = [
            SourceEdge(
                id=edge.id,
                source_id=edge.source_id,
                target_id=edge.target_id,
                relationship=edge.relationship,
                confidence=edge.confidence,
                detected_by=edge.detected_by,
                evidence=edge.evidence,
            )
            for edge in edges
        ]
    finally:
        canonical.close()

    by_id = {UUID(row["source_id"]): row for row in selected_rows}
    return by_id, clones, edge_clones


def _event(db: Session) -> Event:
    event = Event(
        id=BENCHMARK_EVENT_ID,
        title="Jev model launch / emergence and early validation episode",
        event_type="MODEL_LAUNCH_EARLY_VALIDATION",
        actors=["TypeSafe AI / Jev authors and ecosystem participants"],
        action="launch, explain, test, and early-validate Jev",
        object="Jev model",
        time_context="2026-09-16 through 2026-09-20 emergence episode",
        summary=(
            "Jev emerges publicly, attracts cross-platform technical discussion, "
            "and accumulates early demonstrations, explanations, and validation claims."
        ),
        current_state="benchmark replay",
        confidence=0.5,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    return event


def _membership(db: Session, event: Event, source_id: UUID) -> None:
    db.add(
        EventMembershipAssertion(
            workspace_id="local-default",
            event_id=event.id,
            source_id=source_id,
            frame_ids=[],
            action="ASSERT",
            membership="REPORTS_EVENT",
            contextual_role_fields={
                "origin": "PHASE17_JEV_BENCHMARK_EVENT_GOLD",
                "eval_only": True,
            },
            audit_run_id=None,
            authority_policy_version="phase17-jev-benchmark-event-gold-v0.1",
            authority_epoch=1,
            authority_status="AUTHORIZED",
            supersedes_assertion_id=None,
        )
    )


def _unit_digest(units: list[dict]) -> str:
    return _stable_digest(
        [
            {
                "unit_id": row.get("unit_id"),
                "statement": row.get("statement"),
                "epistemic_status": row.get("epistemic_status"),
                "confidence": row.get("confidence"),
                "supports": row.get("supports"),
            }
            for row in units
        ]
    )


def _observation(
    db: Session,
    *,
    event: Event,
    source: Source,
    hydration_row: dict,
    supporting_source_ids: list[UUID],
) -> EventObservationV01:
    units = list(hydration_row.get("projected_units") or [])
    unit_refs = tuple(
        sorted(
            {
                str(row.get("unit_id") or "").strip()
                for row in units
                if str(row.get("unit_id") or "").strip()
            }
        )
    )
    semantic_digest = _unit_digest(units)

    evidence_time = (
        _parse_time(hydration_row.get("source_published_at"))
        or _parse_time(hydration_row.get("trace_published_at"))
        or _parse_time(hydration_row.get("earliest_observed_at"))
        or _parse_time(hydration_row.get("source_ingested_at"))
    )
    ingest_time = (
        _parse_time(hydration_row.get("source_ingested_at"))
        or _parse_time(hydration_row.get("earliest_observed_at"))
        or evidence_time
    )
    if evidence_time is None or ingest_time is None:
        raise RuntimeError(f"Missing evidence/ingest time for Source {source.id}")

    relational = freeze_analysis_relational_context(db, supporting_source_ids)
    return EventObservationV01(
        event_id=event.id,
        observation_key=observation_key_for(
            event_id=event.id,
            source=source,
            snapshot=None,
            semantic_input_digests=(f"hydrated:{semantic_digest}",),
        ),
        source_id=source.id,
        source_snapshot_id=None,
        frame_ids=(),
        semantic_input_digests=(f"hydrated:{semantic_digest}",),
        evidence_time=evidence_time,
        ingest_time=ingest_time,
        world_time=None,
        provenance_digest=relational.digest,
        audited_semantic_unit_refs=unit_refs,
    )


def _latest_source_baseline(units: list[dict]) -> dict:
    return {
        "active_unit_refs": sorted(
            str(row.get("unit_id"))
            for row in units
            if row.get("unit_id")
        ),
        "statements": [
            str(row.get("statement") or "")
            for row in units
            if str(row.get("statement") or "").strip()
        ],
    }


def run(
    *,
    limit: int | None = None,
    projection_path: Path | None = None,
    checkpoint_path: Path | None = None,
    resume: bool = False,
) -> dict:
    projection_path = (projection_path or _latest_full_projection()).resolve()
    projection = json.loads(projection_path.read_text())
    projection_digest = _file_digest(projection_path)
    fixture = json.loads(FIXTURE.read_text())
    checkpoint_path = (checkpoint_path or DEFAULT_CHECKPOINT).resolve()

    if projection.get("status") != "EVAL_ONLY_EVENT_GOLD_SEMANTIC_PROJECTION_COMPLETE":
        raise RuntimeError("Longitudinal replay requires a completed Event-Gold projection artifact")

    by_source_id, source_clones, edge_clones = _load_source_graph(projection)

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    db = Session(engine)

    try:
        db.add_all(source_clones)
        db.flush()
        db.add_all(edge_clones)
        db.flush()

        event = _event(db)
        selected_source_ids = sorted(by_source_id, key=str)
        for source_id in selected_source_ids:
            _membership(db, event, source_id)
        db.flush()

        # Evidence chronology is independent of crawler/processing order.
        hydrated_rows = [
            row for row in projection["items"]
            if row.get("status") == "OK" and row.get("source_id")
        ]
        hydrated_rows.sort(
            key=lambda row: (
                _parse_time(row.get("source_published_at"))
                or _parse_time(row.get("trace_published_at"))
                or _parse_time(row.get("earliest_observed_at"))
                or _parse_time(row.get("source_ingested_at"))
                or datetime.max.replace(tzinfo=timezone.utc),
                str(row.get("source_id")),
            )
        )
        if limit is not None:
            hydrated_rows = hydrated_rows[:limit]

        previous_slot_state: SemanticSlotStateV01 | None = None
        current_event_state = None
        supporting_source_ids: list[UUID] = []
        full_history_refs: set[str] = set()
        trajectory: list[dict] = []
        seen_observation_keys: set[str] = set()
        semantic_unit_by_ref: dict[str, dict] = {}
        replayed_from_checkpoint = 0

        persisted_trajectory: list[dict] = []
        if resume:
            if not checkpoint_path.exists():
                raise RuntimeError(f"Resume requested but checkpoint does not exist: {checkpoint_path}")
            checkpoint = json.loads(checkpoint_path.read_text())
            _validate_checkpoint_identity(
                checkpoint,
                projection_path=projection_path,
                projection_digest=projection_digest,
                items_requested=len(hydrated_rows),
            )
            persisted_trajectory = list(checkpoint.get("trajectory") or [])
            if len(persisted_trajectory) > len(hydrated_rows):
                raise RuntimeError("Checkpoint trajectory is longer than the requested frozen trace")

        # Deterministically reconstruct the prefix from persisted admitted SlotDelta records.
        # No LLM Decide call is allowed during this replay path.
        for ordinal, persisted in enumerate(persisted_trajectory, start=1):
            row = hydrated_rows[ordinal - 1]
            source_id = UUID(row["source_id"])
            if str(source_id) != persisted.get("source_id"):
                raise RuntimeError(
                    f"Checkpoint/source ordering mismatch at ordinal {ordinal}: "
                    f"{persisted.get('source_id')} != {source_id}"
                )
            source = db.get(Source, source_id)
            if source is None:
                raise RuntimeError(f"Benchmark Source missing from eval DB: {source_id}")
            if source_id not in supporting_source_ids:
                supporting_source_ids.append(source_id)

            observation = _observation(
                db,
                event=event,
                source=source,
                hydration_row=row,
                supporting_source_ids=supporting_source_ids,
            )
            if observation.observation_key != persisted.get("observation_key"):
                raise RuntimeError(
                    f"Checkpoint observation_key mismatch at ordinal {ordinal}"
                )
            if observation.observation_key in seen_observation_keys:
                raise RuntimeError(
                    f"Duplicate observation in checkpoint replay: {observation.observation_key}"
                )
            seen_observation_keys.add(observation.observation_key)

            row_units = list(row.get("projected_units") or [])
            for unit in row_units:
                unit_id = str(unit.get("unit_id") or "").strip()
                if unit_id:
                    semantic_unit_by_ref[unit_id] = unit

            persisted_delta = persisted.get("slot_delta")
            delta = (
                SlotDeltaV01.model_validate(persisted_delta)
                if persisted_delta is not None
                else None
            )
            applied = apply_slot_delta(
                db,
                event_id=event.id,
                previous=previous_slot_state,
                observation=observation,
                delta=delta,
                supporting_source_ids=supporting_source_ids,
            )
            next_slot_state = applied.slot_state
            next_state = applied.event_state
            expected_slot_digest = persisted["slot_state_digest"]
            if next_slot_state.state_digest != expected_slot_digest:
                raise RuntimeError(
                    "Deterministic Slot Apply replay digest mismatch at ordinal "
                    f"{ordinal}: {next_slot_state.state_digest} != {expected_slot_digest}"
                )
            if next_slot_state.model_dump(mode="json") != persisted["slot_state"]:
                raise RuntimeError(
                    f"Deterministic Slot Apply replay state mismatch at ordinal {ordinal}"
                )
            expected_digest = persisted["recursive_state_digest"]
            if next_state.state_digest != expected_digest:
                raise RuntimeError(
                    "Deterministic EventState replay digest mismatch at ordinal "
                    f"{ordinal}: {next_state.state_digest} != {expected_digest}"
                )
            if next_state.model_dump(mode="json") != persisted["recursive_state"]:
                raise RuntimeError(
                    f"Deterministic EventState replay mismatch at ordinal {ordinal}"
                )

            latest = _latest_source_baseline(row_units)
            full_history_refs.update(latest["active_unit_refs"])
            trajectory.append(persisted)
            previous_slot_state = next_slot_state
            current_event_state = next_state
            replayed_from_checkpoint += 1
            print(
                "REPLAY",
                ordinal,
                "/",
                len(hydrated_rows),
                persisted["delta_kind"],
                "slot_digest_ok",
                next_slot_state.state_digest,
                "event_digest_ok",
                next_state.state_digest,
            )

        for ordinal, row in enumerate(
            hydrated_rows[len(persisted_trajectory):],
            start=len(persisted_trajectory) + 1,
        ):
            source_id = UUID(row["source_id"])
            source = db.get(Source, source_id)
            if source is None:
                raise RuntimeError(f"Benchmark Source missing from eval DB: {source_id}")
            if source_id not in supporting_source_ids:
                supporting_source_ids.append(source_id)

            observation = _observation(
                db,
                event=event,
                source=source,
                hydration_row=row,
                supporting_source_ids=supporting_source_ids,
            )
            if observation.observation_key in seen_observation_keys:
                raise RuntimeError(
                    f"Duplicate observation in frozen trace: {observation.observation_key}"
                )
            seen_observation_keys.add(observation.observation_key)

            new_units = list(row.get("projected_units") or [])
            for unit in new_units:
                unit_id = str(unit.get("unit_id") or "").strip()
                if unit_id:
                    semantic_unit_by_ref[unit_id] = unit

            if not new_units:
                if previous_slot_state is None:
                    raise RuntimeError(
                        f"First benchmark observation {source_id} has zero projected Event units"
                    )
                delta = None
                flatmap_audit = None
                keyby_audit = None
            else:
                previous_support_units = []
                if previous_slot_state is not None:
                    previous_support_refs = sorted(
                        {
                            ref
                            for slot in previous_slot_state.slots
                            for ref in slot.support_refs
                        }
                    )
                    missing_previous_support = [
                        ref
                        for ref in previous_support_refs
                        if ref not in semantic_unit_by_ref
                    ]
                    if missing_previous_support:
                        raise RuntimeError(
                            "Missing dereferenced semantic units for previous current-slot support: "
                            + ", ".join(missing_previous_support)
                        )
                    previous_support_units = [
                        semantic_unit_by_ref[ref]
                        for ref in previous_support_refs
                    ]
                decision = decide_slot_delta_two_stage(
                    event_identity={
                        "title": event.title,
                        "event_type": event.event_type,
                        "actors": list(event.actors or []),
                        "action": event.action,
                        "object": event.object,
                        "time_context": event.time_context,
                    },
                    previous=previous_slot_state,
                    observation=observation,
                    previous_support_units=previous_support_units,
                    new_semantic_units=new_units,
                    chat_fn=chat_json,
                )
                delta = decision.delta
                flatmap_audit = decision.flatmap.model_dump(mode="json")
                keyby_audit = decision.keyby_draft.model_dump(mode="json")

            applied = apply_slot_delta(
                db,
                event_id=event.id,
                previous=previous_slot_state,
                observation=observation,
                delta=delta,
                supporting_source_ids=supporting_source_ids,
            )
            next_slot_state = applied.slot_state
            next_state = applied.event_state
            latest = _latest_source_baseline(new_units)
            full_history_refs.update(latest["active_unit_refs"])
            trajectory.append(
                {
                    "ordinal": ordinal,
                    "source_id": str(source_id),
                    "title": row.get("title"),
                    "evidence_time": observation.evidence_time.isoformat(),
                    "observation_key": observation.observation_key,
                    "new_event_unit_count": len(new_units),
                    "delta_kind": _delta_label(delta),
                    "slot_delta": (
                        delta.model_dump(mode="json") if delta is not None else None
                    ),
                    "flatmap": flatmap_audit,
                    "keyby_draft": keyby_audit,
                    "delta_rationale": (
                        delta.rationale if delta is not None else None
                    ),
                    "slot_state": next_slot_state.model_dump(mode="json"),
                    "slot_state_digest": next_slot_state.state_digest,
                    "current_slot_count": len(next_slot_state.slots),
                    "recursive_state": next_state.model_dump(mode="json"),
                    "latest_source_baseline": latest,
                    "full_history_bag": {
                        "active_unit_ref_count": len(full_history_refs),
                    },
                    "recursive_active_ref_count": len(
                        next_state.world_state.active_semantic_unit_refs
                    ),
                    "recursive_synopsis_chars": len(
                        next_state.world_state.synopsis
                    ),
                    "recursive_state_digest": next_state.state_digest,
                }
            )
            previous_slot_state = next_slot_state
            current_event_state = next_state
            _write_checkpoint(
                checkpoint_path=checkpoint_path,
                projection_path=projection_path,
                projection_digest=projection_digest,
                items_requested=len(hydrated_rows),
                trajectory=trajectory,
                status="IN_PROGRESS",
            )
            print(
                ordinal,
                "/",
                len(hydrated_rows),
                _delta_label(delta),
                "new_units",
                len(new_units),
                "slots",
                len(next_slot_state.slots),
                "active_refs",
                len(next_state.world_state.active_semantic_unit_refs),
                "independent",
                next_state.evidence_state.independent_source_count,
                "secondary",
                next_state.evidence_state.secondary_report_count,
                next_state.world_state.status,
            )

        mutation_counts = {"CREATE": 0, "UPSERT": 0, "CONTEST": 0, "NONE": 0}
        observations_with_create = 0
        observations_with_upsert = 0
        for row in trajectory:
            persisted_delta = row.get("slot_delta")
            if persisted_delta is None:
                mutation_counts["NONE"] += 1
                continue
            modes = [mutation["mode"] for mutation in persisted_delta.get("mutations", [])]
            observations_with_create += int("CREATE" in modes)
            observations_with_upsert += int(
                "UPSERT" in modes or "CONTEST" in modes
            )
            for mode in modes:
                mutation_counts[mode] = mutation_counts.get(mode, 0) + 1

        _write_checkpoint(
            checkpoint_path=checkpoint_path,
            projection_path=projection_path,
            projection_digest=projection_digest,
            items_requested=len(hydrated_rows),
            trajectory=trajectory,
            status="COMPLETE",
        )

        return {
            "run_version": RUN_VERSION,
            "status": "REAL_MODEL_LONGITUDINAL_STATE_REPLAY_COMPLETE",
            "projection_artifact": str(projection_path.relative_to(ROOT)),
            "projection_digest": projection_digest,
            "decider_contract": TWO_STAGE_DECIDER_CONTRACT,
        "flatmap_contract": PROPOSITION_FLATMAP_CONTRACT,
        "keyby_contract": SEMANTIC_KEYBY_CONTRACT,
            "slot_delta_contract": SLOT_DELTA_CONTRACT,
            "slot_state_contract": SLOT_STATE_CONTRACT,
            "applier_contract": SLOT_APPLIER_CONTRACT,
            "execution_contract": "persisted-slot-delta-apply-v0.1",
            "checkpoint_artifact": str(checkpoint_path.relative_to(ROOT)),
            "replayed_from_checkpoint": replayed_from_checkpoint,
            "projection_run_version": projection["run_version"],
            "hydration_artifact": projection.get("hydration_artifact"),
            "benchmark_event_id": str(BENCHMARK_EVENT_ID),
            "fixture_contract": fixture["contract"],
            "human_gold_used_for_tuning": False,
            "items_requested": len(hydrated_rows),
            "trajectory": trajectory,
            "summary": {
                "observations": len(trajectory),
                "mutation_counts": mutation_counts,
                "observations_with_create": observations_with_create,
                "observations_with_upsert": observations_with_upsert,
                "final_slot_state": (
                    previous_slot_state.model_dump(mode="json")
                    if previous_slot_state is not None
                    else None
                ),
                "final_state": (
                    current_event_state.model_dump(mode="json")
                    if current_event_state is not None
                    else None
                ),
                "final_current_slot_count": (
                    len(previous_slot_state.slots)
                    if previous_slot_state is not None
                    else 0
                ),
                "final_recursive_active_ref_count": (
                    len(current_event_state.world_state.active_semantic_unit_refs)
                    if current_event_state is not None
                    else 0
                ),
                "final_full_history_ref_count": len(full_history_refs),
                "final_active_ref_ratio_vs_history": (
                    (
                        len(current_event_state.world_state.active_semantic_unit_refs)
                        / len(full_history_refs)
                    )
                    if current_event_state is not None and full_history_refs
                    else None
                ),
                "max_current_slot_count": max(
                    (row["current_slot_count"] for row in trajectory),
                    default=0,
                ),
                "max_recursive_active_ref_count": max(
                    (row["recursive_active_ref_count"] for row in trajectory),
                    default=0,
                ),
                "max_recursive_synopsis_chars": max(
                    (row["recursive_synopsis_chars"] for row in trajectory),
                    default=0,
                ),
                "status_sequence": [
                    row["recursive_state"]["world_state"]["status"]
                    for row in trajectory
                ],
                "status_change_count": sum(
                    1
                    for previous_row, current_row in zip(
                        trajectory,
                        trajectory[1:],
                    )
                    if previous_row["recursive_state"]["world_state"]["status"]
                    != current_row["recursive_state"]["world_state"]["status"]
                ),
                "source_edge_count_copied": len(edge_clones),
                "selected_source_count": len(selected_source_ids),
            },
            "guardrails": [
                "Full frozen Event-Gold semantic projection artifact required.",
                "Projection contains only selections over already-audited semantic unit ids.",
                "In-memory benchmark Event uses frozen Event Gold; canonical historical Event topology is not rewritten.",
                "Original Source UUIDs and eligible provenance edges are copied read-only into the eval database.",
                "Observations are processed by evidence_time, not ingest order.",
                "Configured real LLM is used only for new Proposition FlatMap + Semantic KeyBy calls; Slot Apply is deterministic.",
                "Each successful observation is durably checkpointed with the admitted SlotDelta or explicit NONE plus materialized slot/event states.",
                "Resume replays persisted SlotDelta records through deterministic Slot Apply and verifies both slot-state and EventState digests before any new LLM call.",
                "Checkpoint resume is rejected if projection digest or FlatMap/KeyBy/SlotDelta/SlotState/Apply contract identity changes.",
                "Human Gold is not supplied to Decide/Apply and is not used for parameter tuning.",
                "Latest Source and Full History Bag are representation baselines only.",
                "No production EventRevision/Attention/WATCH/Delivery writes.",
            ],
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--projection-artifact", type=Path, default=None)
    parser.add_argument("--checkpoint-path", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    report = run(
        limit=args.limit,
        projection_path=args.projection_artifact,
        checkpoint_path=args.checkpoint_path,
        resume=args.resume,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_n{args.limit}" if args.limit is not None else "_full"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}{suffix}_{stamp}.json"
    _write_json_atomic(path, report)
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("CHECKPOINT_PATH=" + report["checkpoint_artifact"])
    print("REPLAYED_FROM_CHECKPOINT=" + str(report["replayed_from_checkpoint"]))
    print("SUMMARY=" + json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
