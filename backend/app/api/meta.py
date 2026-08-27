from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.kernel import KernelPatch
from app.models.scheduler import AttentionPlan
from app.models.source import Source
from app.models.watch import Watch

router = APIRouter()


@router.get("/home")
def home(db: Session = Depends(get_db)):
    plans = db.execute(select(AttentionPlan)).scalars().all()
    engage = [p for p in plans if p.disposition == "ENGAGE"]
    decision = [p for p in engage if p.expected_output == "DECISION_REVIEW"]
    watch_n = db.execute(select(func.count()).select_from(Watch).where(Watch.status == "ACTIVE")).scalar_one()
    discarded = len([p for p in plans if p.disposition == "DROP"])
    budget = sum((p.cognitive_budget_minutes or 0) for p in engage)
    patches = db.execute(select(func.count()).select_from(KernelPatch).where(KernelPatch.status == "PROPOSED")).scalar_one()
    sources = db.execute(select(func.count()).select_from(Source).where(Source.deleted_at.is_(None))).scalar_one()
    return {
        "decision_items": len(decision),
        "engage_items": len(engage),
        "watch_topics": int(watch_n or 0),
        "discarded": discarded,
        "estimated_attention_minutes": budget,
        "proposed_patches": int(patches or 0),
        "sources": int(sources or 0),
    }
