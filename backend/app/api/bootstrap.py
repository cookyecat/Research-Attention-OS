from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.cognitive.client import LLMError, chat_json
from app.cognitive.prompts import BOOTSTRAP_SYSTEM, BOOTSTRAP_USER
from app.db import get_db
from app.enums import PatchChangeType
from app.models.source import Source
from app.services.kernel_commit import create_patch

router = APIRouter()


class BootstrapIn(BaseModel):
    text: str
    source_ids: list[UUID] = []


@router.post("/bootstrap/propose")
def bootstrap_propose(body: BootstrapIn, db: Session = Depends(get_db)):
    excerpts = []
    for sid in body.source_ids[:8]:
        src = db.get(Source, sid)
        if src and src.content_text:
            excerpts.append((src.title or "") + "\n" + src.content_text[:1500])
    proposals = []
    try:
        data, _meta = chat_json(
            [
                {"role": "system", "content": BOOTSTRAP_SYSTEM},
                {
                    "role": "user",
                    "content": BOOTSTRAP_USER.format(text=body.text[:8000], excerpts="\n---\n".join(excerpts) or "(none)"),
                },
            ]
        )
        raw_list = data.get("proposals") or []
    except LLMError:
        raw_list = _heuristic_bootstrap(body.text)
    patches = []
    for raw in raw_list[:8]:
        node_type = str(raw.get("target_object_type") or "QUESTION").upper()
        title = raw.get("title") or "Untitled"
        payload = raw.get("payload") or {}
        if node_type == "BELIEF":
            payload.setdefault("proposition", title)
            payload.setdefault("scope", "research")
            payload.setdefault("confidence", 0.5)
        patch = create_patch(
            db,
            target_object_type=node_type,
            target_object_id=None,
            change_type=PatchChangeType.CREATE,
            current_state=None,
            proposed_state={"title": title, "status": raw.get("status") or "ACTIVE", "payload": payload, "node_type": node_type},
            reasoning=str(raw.get("reasoning") or "Initial Kernel proposal. Human commit required."),
            proposed_by="AI",
        )
        patches.append(
            {
                "id": str(patch.id),
                "target_object_type": patch.target_object_type,
                "status": patch.status,
                "proposed_state": patch.proposed_state,
                "reasoning": patch.reasoning,
            }
        )
        proposals.append(raw)
    return {"proposals": proposals, "kernel_patches": patches, "note": "Human Accept/Modify/Reject required. AI does not commit Kernel state."}


def _heuristic_bootstrap(text: str) -> list[dict]:
    title = (text.strip().split("\n")[0] or "Research programme")[:180]
    return [
        {
            "target_object_type": "GOAL",
            "title": title,
            "status": "ACTIVE",
            "payload": {"description": text[:800]},
            "reasoning": "Seeded from researcher self-description (heuristic fallback).",
        },
        {
            "target_object_type": "QUESTION",
            "title": "What is the current bottleneck in this programme?",
            "status": "OPEN",
            "payload": {"text": "What is the current bottleneck in this programme?", "scope": "bootstrap"},
            "reasoning": "Open question to keep the Kernel from collapsing into a document dump.",
        },
    ]
