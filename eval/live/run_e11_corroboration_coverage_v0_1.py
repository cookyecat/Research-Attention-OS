from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.db import SessionLocal
from app.services.event_evidence_frames import latest_event_evidence_frames_for_source
from app.services.representation_evidence import build_frame_pair_evidence_bundle


def norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def numeric_anchors(text: str) -> set[str]:
    # Exact diagnostic anchors only; no tolerance/range matching.
    return set(re.findall(r"(?<![A-Za-z])(?:\$|¥|￥)?\d+(?:[.,]\d+)?%?(?:x|倍)?", text or "", flags=re.I))


def actor_names(frame: dict) -> set[str]:
    return {
        norm(row.get("name"))
        for row in frame.get("actors") or []
        if isinstance(row, dict) and norm(row.get("name"))
    }


def action_statuses(frame: dict) -> set[str]:
    return {
        str(row.get("temporal_status") or "").upper()
        for row in frame.get("actions") or []
        if isinstance(row, dict) and row.get("temporal_status")
    }


def quantitative_text(frame: dict) -> str:
    """Exact quantitative evidence only from audited event semantics.

    Deliberately exclude rendered_event_text, support/event ids and actor metadata
    so provenance identifiers cannot masquerade as world-state numbers.
    """
    parts = [frame.get("event_summary") or ""]
    for row in frame.get("actions") or []:
        if isinstance(row, dict):
            parts.append(str(row.get("description") or ""))
    return "\n".join(parts)


def evidence_map(bundle: dict) -> dict[str, dict]:
    return {
        str(row["evidence_id"]): row
        for row in bundle.get("evidence") or []
        if isinstance(row, dict) and row.get("evidence_id")
    }


def resolve_frame(db, spec: dict):
    rows=latest_event_evidence_frames_for_source(db,UUID(spec["source_id"]))
    matches=[row for row in rows if (row.frame_payload or {}).get("event_key")==spec.get("event_key")]
    if len(matches)!=1:
        raise RuntimeError(f"frame resolve failed for {spec}: {len(matches)}")
    return matches[0]


def main():
    corpus=json.loads((ROOT/"eval/fixtures/representation_auditor_v0_1_cases.json").read_text())
    rows=[]
    with SessionLocal() as db:
        for case in corpus["cases"]:
            fa=resolve_frame(db,case["a"])
            fb=resolve_frame(db,case["b"])
            bundle=build_frame_pair_evidence_bundle(db,fa.id,fb.id)
            em=evidence_map(bundle.payload)
            sa=(em.get("SOURCE_A") or {}).get("data") or {}
            sb=(em.get("SOURCE_B") or {}).get("data") or {}
            a=(em.get("FRAME_A") or {}).get("data") or {}
            b=(em.get("FRAME_B") or {}).get("data") or {}
            aa,ab=actor_names(a),actor_names(b)
            na,nb=numeric_anchors(quantitative_text(a)),numeric_anchors(quantitative_text(b))
            status_a,status_b=action_statuses(a),action_statuses(b)
            graph=[
                (x.get("data") or {}).get("relationship")
                for x in bundle.payload.get("evidence") or []
                if isinstance(x,dict) and x.get("kind")=="EXISTING_SOURCE_GRAPH_FACT"
                and (x.get("data") or {}).get("authority_eligible") is True
            ]
            external_a=set(sa.get("external_item_ids") or [])
            external_b=set(sb.get("external_item_ids") or [])
            rows.append({
                "name":case["name"],
                "expected":case["expected"]["event_identity"],
                "same_external_item":bool(external_a & external_b),
                "same_canonical_url":bool(sa.get("canonical_url") and sa.get("canonical_url")==sb.get("canonical_url")),
                "same_content_hash":bool(sa.get("content_hash") and sa.get("content_hash")==sb.get("content_hash")),
                "shared_actor_names":sorted(aa & ab),
                "shared_actor_count":len(aa & ab),
                "shared_numeric_anchors":sorted(na & nb),
                "shared_numeric_count":len(na & nb),
                "shared_action_statuses":sorted(status_a & status_b),
                "shared_action_status_count":len(status_a & status_b),
                "authority_eligible_graph_facts":graph,
            })
    print(json.dumps({"study":"e11-corroboration-coverage-v0.1","rows":rows},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
