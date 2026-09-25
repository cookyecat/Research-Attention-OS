from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.kernel import KernelPatch
from app.models.scheduler import AttentionPlan
from app.models.source import Source
from app.models.watch import Watch
from app.services.source_surface import is_user_visible_source_clause

router = APIRouter()


@router.get("/home")
def home(db: Session = Depends(get_db)):
    engage_items = db.execute(
        select(func.count())
        .select_from(AttentionPlan)
        .where(AttentionPlan.disposition == "ENGAGE")
    ).scalar_one()
    decision_items = db.execute(
        select(func.count())
        .select_from(AttentionPlan)
        .where(
            AttentionPlan.disposition == "ENGAGE",
            AttentionPlan.expected_output == "DECISION_REVIEW",
        )
    ).scalar_one()
    discarded = db.execute(
        select(func.count())
        .select_from(AttentionPlan)
        .where(AttentionPlan.disposition == "DROP")
    ).scalar_one()
    budget = db.execute(
        select(func.coalesce(func.sum(AttentionPlan.cognitive_budget_minutes), 0))
        .where(AttentionPlan.disposition == "ENGAGE")
    ).scalar_one()
    watch_n = db.execute(
        select(func.count()).select_from(Watch).where(Watch.status == "ACTIVE")
    ).scalar_one()
    patches = db.execute(
        select(func.count()).select_from(KernelPatch).where(KernelPatch.status == "PROPOSED")
    ).scalar_one()
    sources = db.execute(
        select(func.count()).select_from(Source).where(
            *is_user_visible_source_clause()
        )
    ).scalar_one()
    return {
        "decision_items": int(decision_items or 0),
        "engage_items": int(engage_items or 0),
        "watch_topics": int(watch_n or 0),
        "discarded": int(discarded or 0),
        "estimated_attention_minutes": int(budget or 0),
        "proposed_patches": int(patches or 0),
        "sources": int(sources or 0),
    }
