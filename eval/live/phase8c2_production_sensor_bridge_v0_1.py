"""Phase 8C.2 candidate: Semantic Sensor v0.2.6 -> Auditor -> production ExtractionResult.

Research implementation only. backend/app owns the injectable bridge interface and never
imports this module. Frozen Sensor/Auditor/Delta/Attention semantics are not redefined here.
"""
from __future__ import annotations

from datetime import timezone
import hashlib
import re
from typing import Any

from app.config import settings
from app.models.source import Source
from app.services.extraction import ExtractionResult, merge_extractions
from app.services.extraction_bridge import ExtractionBridgeResult
from eval.live.phase6b_cognitive_semantics_v0_1 import (
    admitted_epistemic_units,
    audit_epistemic_unit_edge,
    audited_units_to_extraction,
    project_epistemic_unit_edge,
)
from eval.live.raw_source_attention_vertical_slice_v0_1 import (
    audit_event_edges,
    build_audited_event_projection,
    project_event_audit_edges,
)
from eval.live.semantic_evidence_auditor_v0_1_1 import AUDITOR_VERSION, prompt_sha256 as auditor_prompt_sha256
from eval.live.semantic_evidence_extractor_v0_2_6 import (
    EXTRACTOR_VERSION,
    estimate_semantic_evidence_v0_2_6,
    prompt_sha256 as sensor_prompt_sha256,
)
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource, _render_text_paragraphs

BRIDGE_VERSION = "phase8c2-production-sensor-bridge-v0.1"
SOURCE_PACKAGING_VERSION = "production-source-to-semantic-sensor-v0.3-url-provenance-blocks"
URL_PROVENANCE_BLOCK_MAX_CHARS = 580

_CONFIDENCE_ORDER = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


class ProductionSensorBridgeError(RuntimeError):
    pass


def _iso(value) -> str:
    if value is None:
        return "unknown"
    if getattr(value, "tzinfo", None) is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_blob_sha(text: str) -> str:
    payload = text.encode("utf-8")
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _split_long_provenance_block(text: str, *, max_chars: int = URL_PROVENANCE_BLOCK_MAX_CHARS) -> list[str]:
    block = str(text or "").strip()
    if not block:
        return []
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", block) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) <= max_chars:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
                continue
            chunks.append(current)
            current = sentence
            continue
        if current:
            chunks.append(current)
            current = ""
        rest = sentence
        while len(rest) > max_chars:
            cut = rest.rfind(" ", 0, max_chars + 1)
            if cut < max_chars // 2:
                cut = max_chars
            chunks.append(rest[:cut].strip())
            rest = rest[cut:].strip()
        current = rest
    if current:
        chunks.append(current)
    return chunks


def _render_url_connector_blocks(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks: list[str] = []
    for raw_block in normalized.split("\n"):
        block = raw_block.strip()
        if block:
            blocks.extend(_split_long_provenance_block(block))
    return "\n\n".join(
        f"[PARA {idx:04d}]\n{block}" for idx, block in enumerate(blocks, start=1)
    )


def _render_production_source_text(source: Source, raw: str) -> str:
    source_type = str(source.source_type or "").upper()
    ingestion_method = str(source.ingestion_method or "").upper()
    if source_type == "URL" or ingestion_method == "URL_FETCH":
        return _render_url_connector_blocks(raw)
    return _render_text_paragraphs(raw)


def production_source_to_sensor_source(source: Source) -> LoadedSemanticSource:
    raw = str(source.content_text or "").strip()
    if not raw:
        raise ProductionSensorBridgeError(f"source {source.id} has no content_text")
    rendered = _render_production_source_text(source, raw)
    locator = source.canonical_url or f"raos://source/{source.id}"
    captured = _iso(source.ingested_at or source.created_at)
    return LoadedSemanticSource(
        source_id=str(source.id),
        path=str(locator),
        media_type=str(source.source_type or "TEXT"),
        git_blob_sha=_git_blob_sha(raw),
        file_sha256=_sha256(raw),
        text_sha256=_sha256(rendered),
        char_count=len(rendered),
        page_count=None,
        rendered_text=rendered,
        published_at=_iso(source.published_at),
        updated_at="unknown",
        captured_at=captured,
    )


def _as_of(source: Source) -> str:
    value = source.ingested_at or source.created_at
    if value is None:
        raise ProductionSensorBridgeError(f"source {source.id} has no stable ingestion timestamp")
    return _iso(value)

def _event_unit_epistemics(frame: dict[str, Any], row: dict[str, Any]) -> tuple[str, str]:
    evidence_by_id = {
        str(item["evidence_id"]): item
        for item in frame.get("evidence") or []
        if item.get("evidence_id")
    }
    cited = [evidence_by_id[sid] for sid in row.get("support_ids") or [] if sid in evidence_by_id]
    statuses = {str(item.get("epistemic_status") or "SOURCE_CLAIM") for item in cited}
    if statuses == {"DIRECT_OBSERVATION"}:
        status = "DIRECT_OBSERVATION"
    elif statuses == {"EXTRACTOR_INFERENCE"}:
        status = "EXTRACTOR_INFERENCE"
    else:
        status = "SOURCE_CLAIM"

    confidences = [str(item.get("confidence") or "UNKNOWN").upper() for item in cited]
    confidence = min(confidences, key=lambda x: _CONFIDENCE_ORDER.get(x, 0)) if confidences else "UNKNOWN"
    return status, confidence


def _admitted_event_units(frame: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[list[dict], dict]:
    projection = build_audited_event_projection(frame, rows)
    if projection["routing_status"] != "ROUTABLE":
        return [], projection

    units: list[dict[str, Any]] = []
    for row in rows:
        result = row.get("audit_result") or {}
        if not (row.get("scorable") and result.get("verdict") == "SUFFICIENT"):
            continue
        status, confidence = _event_unit_epistemics(frame, row)
        units.append(
            {
                "unit_id": f"{row['event_id']}:{row['group']}:{row['index'] + 1}",
                "statement": str(row["semantic_object"]),
                "epistemic_status": status,
                "confidence": confidence,
                "supports": list(row.get("evidence") or []),
            }
        )
    return units, projection


def _fail_on_auditor_transport_error(rows: list[dict[str, Any]], *, source_id: str) -> None:
    failures = [
        row for row in rows
        if not row.get("scorable") and row.get("failure_kind") not in {None, "no_cited_evidence"}
    ]
    if failures:
        kinds = sorted({str(row.get("failure_kind")) for row in failures})
        raise ProductionSensorBridgeError(
            f"Auditor transport/schema failure for source {source_id}: {kinds}"
        )


def _audit_non_event_units(source_id: str, units: list[dict], *, chat_fn=None):
    rows = [
        audit_epistemic_unit_edge(project_epistemic_unit_edge(source_id, unit), chat_fn=chat_fn)
        for unit in units
    ]
    _fail_on_auditor_transport_error(rows, source_id=source_id)
    return rows, admitted_epistemic_units(rows)


def _audit_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for row in rows:
        result = row.get("audit_result") or {}
        verdict = str(result.get("verdict") or "UNSCORABLE")
        reason = str(result.get("reason_code") or row.get("failure_kind") or "UNSCORABLE")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "n_edges": len(rows),
        "n_scorable": sum(bool(row.get("scorable")) for row in rows),
        "verdict_counts": dict(sorted(verdicts.items())),
        "reason_counts": dict(sorted(reasons.items())),
    }


class SemanticSensorProductionBridgeV0_1:
    def __init__(self, *, sensor_chat_fn=None, auditor_chat_fn=None):
        self.sensor_chat_fn = sensor_chat_fn
        self.auditor_chat_fn = auditor_chat_fn

    def execution_snapshot(self) -> dict[str, Any]:
        return {
            "bridge_version": BRIDGE_VERSION,
            "source_packaging_version": SOURCE_PACKAGING_VERSION,
            "source_packaging_max_block_chars": URL_PROVENANCE_BLOCK_MAX_CHARS,
            "sensor_version": EXTRACTOR_VERSION,
            "sensor_prompt_sha256": sensor_prompt_sha256(),
            "auditor_version": AUDITOR_VERSION,
            "auditor_prompt_sha256": auditor_prompt_sha256(),
            "requested_model": settings.llm_model,
        }

    def _extract_one(self, source: Source) -> tuple[ExtractionResult, dict[str, Any]]:
        sensor_source = production_source_to_sensor_source(source)
        result = estimate_semantic_evidence_v0_2_6(
            sensor_source,
            as_of=_as_of(source),
            chat_fn=self.sensor_chat_fn,
        )
        if not result.get("scorable") or not result.get("batch"):
            raise ProductionSensorBridgeError(
                f"Sensor failure for source {source.id}: {result.get('failure_kind')} {result.get('error')}"
            )
        batch = result["batch"]
        source_id = str(source.id)
        non_rows, non_admitted = _audit_non_event_units(
            source_id,
            list(batch.get("non_event_units") or []),
            chat_fn=self.auditor_chat_fn,
        )
        event_units: list[dict[str, Any]] = []
        event_diagnostics: list[dict[str, Any]] = []
        for frame in batch.get("event_frames") or []:
            edges = project_event_audit_edges(source_id, frame)
            rows = audit_event_edges(edges, chat_fn=self.auditor_chat_fn)
            _fail_on_auditor_transport_error(rows, source_id=source_id)
            admitted, projection = _admitted_event_units(frame, rows)
            event_units.extend(admitted)
            event_diagnostics.append(
                {
                    "event_id": projection["event_id"],
                    "routing_status": projection["routing_status"],
                    "sensor_summary_diagnostic_only": projection["sensor_event_summary_diagnostic_only"],
                    "n_edges": len(rows),
                    "n_admitted_edges": len(admitted),
                    "n_rejected_or_unscorable": len(projection["rejected_or_unscorable_objects"]),
                    "audit": _audit_summary(rows),
                }
            )

        admitted_units = [*event_units, *non_admitted]
        extraction = audited_units_to_extraction(admitted_units)
        extraction.event_title = source.title
        diagnostics = {
            "source_id": source_id,
            "sensor": {
                "n_event_frames": len(batch.get("event_frames") or []),
                "n_non_event_units": len(batch.get("non_event_units") or []),
                "repair_used": bool(result.get("repair_used")),
            },
            "auditor": {
                "non_event": _audit_summary(non_rows),
                "n_non_event_admitted": len(non_admitted),
                "n_event_units_admitted": len(event_units),
            },
            "events": event_diagnostics,
            "n_total_admitted_units": len(admitted_units),
        }
        return extraction, diagnostics

    def extract(self, source: Source, extra_sources: list[Source]) -> ExtractionBridgeResult:
        ordered = [source, *sorted(extra_sources, key=lambda item: str(item.id))]
        parts: list[ExtractionResult] = []
        source_diagnostics: list[dict[str, Any]] = []
        for item in ordered:
            extraction, diagnostics = self._extract_one(item)
            parts.append(extraction)
            source_diagnostics.append(diagnostics)
        merged = merge_extractions(*parts) if len(parts) > 1 else parts[0]
        return ExtractionBridgeResult(
            extraction=merged,
            diagnostics={
                "bridge_version": BRIDGE_VERSION,
                "evidence_gate": "semantic-sensor-v0.2.6-plus-auditor-v0.1.1",
                "legacy_reason_evidence": "intentionally-bypassed-by-bridge",
                "sources": source_diagnostics,
            },
        )
