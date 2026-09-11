from __future__ import annotations

import json
from typing import Literal
from pydantic import Field
from app.cognitive.schemas import StrictModel

VERSION="phase10d6j-relation-support-directness-v0.1"
Fit=Literal["DIRECT","PARTIAL","INSUFFICIENT","CONTRADICTS_OPERATION"]

SYSTEM_PROMPT="""Audit whether cited semantic evidence justifies a proposed cognitive relation on an exact Kernel proposition.
Do NOT judge source prestige, general truth, importance, Attention, or confidence. Do NOT emit numeric scores.

Fit classes:
- DIRECT: the support directly bears on the target proposition at matching scope and supports the stated REINFORCE/CHALLENGE direction.
- PARTIAL: materially relevant but needs a bounded extrapolation or has a meaningful scope gap.
- INSUFFICIENT: topical/related evidence does not justify this operation on this target proposition.
- CONTRADICTS_OPERATION: the support more naturally points opposite the proposed REINFORCE/CHALLENGE direction.

Treat scope words literally. Evidence about broad computer use is not automatically evidence about the fastest embodied-control loop. Absence of a metric in one article is not automatically proof of a general evaluation bottleneck. Preserve item_id exactly. Return JSON only."""

class DirectnessClassification(StrictModel):
    item_id:str=Field(min_length=1)
    fit:Fit
    reason:str=Field(min_length=1)

class DirectnessResponse(StrictModel):
    classifications:list[DirectnessClassification]

def build_user_prompt(items:list[dict])->str:
    shape={'classifications':[{'item_id':'A::A-1::2','fit':'DIRECT','reason':'short scope/direction rationale'}]}
    return 'Relations to audit:\n'+json.dumps(items,ensure_ascii=False)+'\n\nReturn JSON in exactly this shape:\n'+json.dumps(shape,ensure_ascii=False)
