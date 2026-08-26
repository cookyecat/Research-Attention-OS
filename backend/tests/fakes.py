"""Scripted OpenAI-compatible chat for tests. No paid API.

Inspects prompt stage + source semantics so paraphrase/generalization
tests can run without keyword-identical A–O fixtures.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.cognitive.client import LLMError

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

META = {"latency_ms": 3, "prompt_tokens": 40, "completion_tokens": 20, "model": "fake-raos"}

HYPE = ("reimagine", "lifestyle", "delight", "game-changing", "unlock a revolutionary", "magical", "best life", "pure adjectives")


def _split_marker(user: str, marker: str) -> tuple[str, str]:
    idx = user.lower().find(marker.lower())
    if idx < 0:
        return user, ""
    return user[:idx], user[idx + len(marker) :]


def _load_json_blob(user: str) -> Any:
    text = user.strip()
    for candidate in (text, text.split("\n", 1)[0]):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    start = text.find("[")
    if start < 0:
        start = text.find("{")
    if start >= 0:
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            return None
    return None


class SemanticFakeChat:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[str] = []

    def __call__(self, messages: list[dict[str, str]], **_kwargs) -> tuple[dict, dict]:
        if self.fail:
            raise LLMError("simulated provider failure")
        system = (messages[0].get("content") or "").lower()
        user = messages[1].get("content") or ""
        self.calls.append(system[:80])
        if "extraction stage" in system:
            return self._extract(user), META
        if "match extracted" in system or "embedding retrieval" in system:
            return self._match(user), META
        if "relate claims" in system or "stances:" in system:
            return self._evidence(user), META
        if (
            "cognitive impact" in system
            or "judge scheduler" in system
            or "you do not choose drop" in system
        ):
            return self._impact(user), META
        if "model delta" in system or "what this information could change" in system:
            return self._delta(user), META
        if "initial cognitive kernel" in system:
            return {
                "proposals": [
                    {
                        "target_object_type": "GOAL",
                        "title": "Research programme",
                        "status": "ACTIVE",
                        "payload": {"description": user[:400]},
                        "reasoning": "fake bootstrap",
                    }
                ]
            }, META
        return {"ok": True}, META

    def _extract(self, user: str) -> dict:
        low = user.lower()
        claims: list[dict] = []
        observations: list[dict] = []
        inferences: list[dict] = []
        future: list[str] = []
        technical: list[str] = []
        promo: list[str] = []

        def add_claim(text: str, claim_type: str, attr: str = "COMPANY", who: str | None = "company"):
            claims.append(
                {
                    "text": text,
                    "attributed_to": who,
                    "attribution_type": attr,
                    "claim_type": claim_type,
                    "temporal_status": "FUTURE" if claim_type == "PREDICTIVE" else "CURRENT",
                    "extraction_confidence": 0.7,
                    "source_span": text[:80],
                }
            )

        if "zero-shot" in low or "generaliz" in low:
            add_claim("The company says the robot generalizes zero-shot.", "TECHNICAL", "COMPANY")
            technical.append("generalizes zero-shot")
        if any(k in low for k in ("continuous", "smooth locomotion", "uninterrupted motion", "stable")) and any(
            k in low for k in ("motion", "movement", "locomotion", "fold")
        ):
            add_claim("The company claims the low-level system produces stable, continuous movement.", "TECHNICAL")
            technical.append("stable continuous movement")
        if "agent brain" in low:
            add_claim("The company says the robot uses an agent brain.", "TECHNICAL")
        if any(k in low for k in ("end-to-end", "unified policy", "sensory input directly", "joint commands")):
            add_claim("The founder says end-to-end / a unified policy will replace hierarchical control.", "OPINION", "FOUNDER", "founder")
            technical.append("end-to-end unified policy")
        if any(k in low for k in ("world model", "many bodies", "one world", "swarm")):
            add_claim("A shared world model coordinates multiple robotic units.", "TECHNICAL")
            technical.append("shared world model")
        if any(k in low for k in ("will be released", "is planned", "planned for", "not yet released")):
            add_claim("OrbitBench will be released. First in-orbit validation is planned.", "PREDICTIVE")
            future.append("OrbitBench will be released")
        if any(k in low for k in ("revolutionary", "seamless", "game-changing", "unprecedented")):
            add_claim("The company calls it a revolutionary seamless leap.", "PROMOTIONAL")
            promo.append("revolutionary seamless")
        if "latency" in low and "energy" in low:
            add_claim("High-frequency embodied control may face latency and energy costs.", "TECHNICAL", "USER", "user")
        if any(k in low for k in ("necessary for high-frequency", "opposite of the belief", "large unified models are necessary")):
            add_claim("A paper argues large unified models are necessary for high-frequency embodied motor control.", "TECHNICAL", "PAPER", "paper")
        if any(k in low for k in ("scale differently", "semantic task intelligence")):
            add_claim("Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently.", "TECHNICAL", "RESEARCHER")
        if any(k in low for k in ("mmlu", "minor model version")):
            add_claim("A major company announces a minor model version with slightly better MMLU.", "FACTUAL")
        if any(k in low for k in ("launches robot", "launches", "unveils")) and "today" in low:
            add_claim("Company X launches robot Y today.", "FACTUAL")
        if any(k in low for k in ("equity", "stake", "ownership", "employment", "labor relationship", "minority")):
            add_claim("Minority ownership did not imply an operating or employment role.", "FACTUAL", "UNKNOWN", None)

        if any(
            k in low
            for k in (
                "pause",
                "dwell",
                "bursts",
                "succeeds once",
                "i saw",
                "demo",
                "video",
                "move then rest",
                "visible halt",
            )
        ):
            observations.append(
                {
                    "text": "The demo shows repeated movement with visible dwell / pause phases (move then rest then move).",
                    "observer": "USER",
                    "observation_type": "DIRECT_VISUAL",
                    "confidence": 0.8,
                    "source_span": "dwell",
                }
            )
        if "succeeds once" in low or "one successful trial" in low:
            observations.append(
                {
                    "text": "In the video, it succeeds once.",
                    "observer": "USER",
                    "observation_type": "DIRECT_VISUAL",
                    "confidence": 0.75,
                    "source_span": "succeeds once",
                }
            )

        if any(
            k in low
            for k in (
                "probably",
                "system is robust",
                "it is robust",
                "suggests robustness",
                "therefore it is robust",
            )
        ):
            add_claim(
                "This probably means the system is robust.",
                "OPINION",
                "UNKNOWN",
                "source",
            )
            inferences.append(
                {
                    "text": "A single successful trial is insufficient to support zero-shot generalization.",
                    "derived_from": "RAOS",
                    "confidence": 0.4,
                }
            )

        if not claims:
            add_claim(user.split("\n", 1)[-1][:280].strip() or "Attributed statement from the source.", "FACTUAL", "UNKNOWN", None)

        marketing = any(k in low for k in ("reimagine", "lifestyle", "delight", "game-changing")) and not technical
        return {
            "event_title": "extracted event",
            "event_summary": None,
            "claims": claims,
            "observations": observations,
            "inferences": inferences,
            "current_facts": [c["text"] for c in claims if c["claim_type"] != "PREDICTIVE"],
            "future_plans": future,
            "technical_claims": technical,
            "promotional_framing": promo,
            "marketing_heavy": marketing,
        }

    def _match(self, user: str) -> dict:
        source, rest = _split_marker(user, "Kernel candidates:")
        low = source.lower()
        motorish = any(
            k in low
            for k in (
                "motor",
                "embodied",
                "fold",
                "humanoid",
                "joint",
                "dwell",
                "pause",
                "latency",
                "end-to-end",
                "unified model",
                "fastest loop",
                "control loop",
            )
        )
        hype = any(k in low for k in HYPE) and not motorish
        cands = _load_json_blob(rest)
        if not isinstance(cands, list):
            cands = []
            for uid in UUID_RE.findall(rest):
                cands.append({"kernel_node_id": uid, "title": "", "text": "", "node_type": ""})
        matches = []
        for cand in cands or []:
            if not isinstance(cand, dict):
                continue
            nid = cand.get("kernel_node_id")
            title = str(cand.get("title") or "")
            text = str(cand.get("text") or "")
            ntype = str(cand.get("node_type") or "")
            blob = f"{title} {text} {ntype}".lower()
            score = 0.15
            rel = "TOPIC"
            if hype:
                continue
            if any(k in blob for k in ("motor", "embodied", "latency", "control")) and any(
                k in low
                for k in (
                    "motor",
                    "embodied",
                    "fold",
                    "humanoid",
                    "joint",
                    "dwell",
                    "pause",
                    "latency",
                    "end-to-end",
                    "unified model",
                    "fastest loop",
                    "control loop",
                )
            ):
                score = 0.86
                rel = "BOTTLENECK" if "latency" in blob else "TOPIC"
            if "collective" in blob or "world model" in blob or "swarm" in blob:
                if any(k in low for k in ("world model", "swarm", "many bodies", "collective", "multi-agent")):
                    score = 0.84
                    rel = "TOPIC"
            if any(k in blob for k in ("equity", "employment", "decision")) or ntype == "DECISION":
                if any(
                    k in low
                    for k in (
                        "equity",
                        "stake",
                        "ownership",
                        "employment",
                        "labor relationship",
                        "minority",
                        "shareholder",
                        "beverage",
                    )
                ):
                    score = 0.9
                    rel = "STRUCTURAL"
            if ("unsuitable" in blob or ntype == "BELIEF") and any(
                k in low for k in ("end-to-end", "unified", "necessary", "opposite", "contradict")
            ):
                score = max(score, 0.8)
            if ("separable" in blob or ntype == "MODEL") and any(
                k in low for k in ("motor", "cognitive", "scale differently", "folding")
            ):
                score = max(score, 0.78)
            if score >= 0.4:
                matches.append(
                    {
                        "kernel_node_id": nid,
                        "relevance_type": rel,
                        "score": score,
                        "reason": f"{rel} match on {title[:80]}",
                    }
                )
        return {"matches": matches}

    def _evidence(self, user: str) -> dict:
        low = user.lower()
        links = []
        if any(k in low for k in ("pause", "dwell", "bursts")) and any(k in low for k in ("continuous", "stable")):
            links.append(
                {
                    "source_role": "OBSERVATION",
                    "source_index": 0,
                    "target_role": "CLAIM",
                    "target_index": 0,
                    "stance": "WEAKENS",
                    "strength": "MODERATE",
                    "confidence": 0.6,
                    "scope": "low-level motion continuity in the demo, not the entire architecture",
                }
            )
        if "succeeds once" in low and "zero-shot" in low:
            links.append(
                {
                    "source_role": "OBSERVATION",
                    "source_index": 0,
                    "target_role": "CLAIM",
                    "target_index": 0,
                    "stance": "WEAKENS",
                    "strength": "WEAK",
                    "confidence": 0.45,
                    "scope": "single trial ≠ generalization",
                }
            )
        return {"links": links}

    def _delta(self, user: str) -> dict:
        source, _rest = _split_marker(user, "Kernel matches:")
        low = source.lower()
        distinctions = []
        questions = []
        hypotheses = []
        impacts = []
        if any(k in low for k in ("pause", "dwell", "continuous", "motor", "fold")) and "launches" not in low:
            distinctions.append(
                "Potential distinction between high-level cognitive/task intelligence and temporal motor performance."
            )
            impacts.append("REFINE")
        if any(k in low for k in ("end-to-end", "unified policy", "hierarchical", "joint commands")):
            questions.append("At which temporal/control layers should end-to-end learning apply?")
            distinctions.append("Do not reduce end-to-end vs hierarchical to a binary good/bad.")
        if any(k in low for k in ("equity", "stake", "employment", "labor", "ownership")):
            distinctions.append("Equity ownership is not the same as an employment relationship.")
            impacts.append("DECISION_REVIEW")
        if "scale differently" in low:
            distinctions.append("Semantic task intelligence and temporal motor intelligence may scale differently.")
        if any(k in low for k in ("scripted", "refute entire")):
            hypotheses.append("Do not infer the system is scripted without independent evidence.")
        summary = distinctions[0] if distinctions else "No committed Kernel change is implied yet."
        return {
            "summary": summary,
            "affected_kernel_nodes": [],
            "distinctions": distinctions,
            "new_questions": questions,
            "possible_hypotheses": hypotheses,
            "decision_implications": ["Review active Decision if structural/decision relevance is high."] if "equity" in low or "stake" in low else [],
            "epistemic_risk": "Insufficient evidence must not become a strong conclusion.",
            "evidence_maturity": 0.4,
            "admission_allowed": bool(distinctions) and "launches robot" not in low,
            "rationale": "Proposal only; human commit required.",
            "what_could_change": distinctions[:],
        }

    def _judge(self, user: str) -> dict:
        return self._impact(user)

    def _impact(self, user: str) -> dict:
        source, rest = _split_marker(user, "Matches:")
        low = source.lower()
        parsed = _load_json_blob(rest)
        matches = parsed if isinstance(parsed, list) else []
        marketing = any(k in low for k in HYPE)
        disagreement = any(
            k in low
            for k in (
                "pause",
                "dwell",
                "opposite",
                "necessary for high-frequency",
                "weakens",
                "continuous",
                "end-to-end",
                "hierarchy",
                "unified policy",
                "contradict",
                "unsuitable",
                "joint commands",
            )
        )
        structural = any(
            str(m.get("rel") or "").upper() == "STRUCTURAL" for m in matches if isinstance(m, dict)
        ) or any(
            k in low for k in ("equity", "stake", "employment", "labor relationship", "ownership", "minority")
        )
        motor = any(
            k in low
            for k in (
                "motor",
                "embodied",
                "humanoid",
                "folding",
                "latency",
                "end-to-end",
                "joint",
                "unified model",
                "fastest loop",
                "control loop",
            )
        )
        hype_only = marketing and not motor
        minor = "minor" in low and "version" in low
        importance = {
            "DECISION": 0.85,
            "BOTTLENECK": 0.8,
            "BELIEF": 0.75,
            "MODEL": 0.75,
            "QUESTION": 0.7,
            "PROJECT": 0.65,
            "GOAL": 0.9,
        }
        effects = []
        if hype_only:
            effects.append(
                {
                    "target_kernel_node_id": None,
                    "effect": "NO_MATERIAL_CHANGE",
                    "change_magnitude": 0.08,
                    "epistemic_strength": 0.1,
                    "target_importance": 0.1,
                    "reason": "Promotional source with no material Kernel effect.",
                    "exploration_candidate": False,
                }
            )
        else:
            for item in matches:
                if not isinstance(item, dict):
                    continue
                ntype = str(item.get("type") or "")
                nid = item.get("id")
                rel = str(item.get("rel") or "").upper()
                score = float(item.get("score") or 0.5)
                if disagreement and ntype == "BELIEF":
                    kind = "CHALLENGE"
                    change = max(score, 0.75)
                elif rel == "STRUCTURAL" or ntype == "DECISION":
                    kind = "REFINE"
                    change = max(score, 0.75)
                elif ntype in {"MODEL", "QUESTION", "BOTTLENECK"}:
                    kind = "REFINE"
                    change = max(score, 0.65)
                elif motor or ntype == "PROJECT":
                    kind = "REFINE"
                    change = max(score, 0.7)
                else:
                    kind = "REINFORCE"
                    change = score
                if minor:
                    kind = "NO_MATERIAL_CHANGE"
                    change = min(change, 0.15)
                epi = 0.22 if marketing else (0.55 if disagreement else 0.32)
                effects.append(
                    {
                        "target_kernel_node_id": nid,
                        "effect": kind,
                        "change_magnitude": change,
                        "epistemic_strength": epi,
                        "target_importance": importance.get(ntype, 0.5),
                        "reason": f"{kind} on {item.get('title') or ntype}",
                        "exploration_candidate": False,
                    }
                )
            if not effects:
                if motor and not hype_only:
                    effects.append(
                        {
                            "target_kernel_node_id": None,
                            "effect": "OPEN_NEW",
                            "change_magnitude": 0.55,
                            "epistemic_strength": 0.3,
                            "target_importance": 0.55,
                            "reason": "No Kernel target; possible new research direction.",
                            "exploration_candidate": True,
                        }
                    )
                else:
                    effects.append(
                        {
                            "target_kernel_node_id": None,
                            "effect": "NO_MATERIAL_CHANGE",
                            "change_magnitude": 0.1,
                            "epistemic_strength": 0.15,
                            "target_importance": 0.2,
                            "reason": "No material Kernel effect.",
                            "exploration_candidate": False,
                        }
                    )
        return {
            "effects": effects,
            "attention_cost": 8 if motor else 2,
            "exploration_candidate": any(e.get("exploration_candidate") for e in effects),
            "evidence_maturity": 0.4,
            "threatens_active_work": "invalidat" in low or ("novelty" in low and "overlap" in low),
            "marketing_heavy": hype_only,
            "high_quality_technical": motor and not hype_only,
            "foundational_paper": ("foundational" in low or "principles of" in low) and not hype_only,
        }


class BoomChat:
    def __call__(self, messages, **_kwargs):
        raise LLMError("provider down")
