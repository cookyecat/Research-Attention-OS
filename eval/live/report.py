from __future__ import annotations

from collections import defaultdict
from typing import Any

from eval.live.schema import LiveCase, gold_status_of


def compute_metrics(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = [r for r in case_rows if r.get("gold_status") == "LABELED"]
    unlabeled_n = sum(1 for r in case_rows if r.get("gold_status") != "LABELED")
    fallback_rows = [r for r in case_rows if _is_rule_fallback(r)]
    model_labeled = [r for r in labeled if not _is_rule_fallback(r)]
    attention = _attention_metrics(model_labeled)
    kernel = _kernel_metrics(model_labeled)
    epistemic = _epistemic_metrics(model_labeled)
    delta = _delta_metrics(model_labeled)
    safety = _safety_metrics(model_labeled)
    by_source_kind = _slice(model_labeled, "source_kind")
    by_task = _slice_tasks(model_labeled)
    return {
        "n_cases": len(case_rows),
        "n_labeled": len(labeled),
        "n_unlabeled": unlabeled_n,
        "n_fallback": len(fallback_rows),
        "n_model_predictions": sum(1 for r in case_rows if r.get("model_prediction") is True),
        "unlabeled_excluded_from_accuracy": True,
        "fallback_excluded_from_model_metrics": True,
        "attention": attention,
        "kernel_matching": kernel,
        "epistemic_separation": epistemic,
        "model_delta": delta,
        "safety": safety,
        "by_source_kind": by_source_kind,
        "by_cognitive_task": by_task,
    }


def _is_rule_fallback(row: dict) -> bool:
    if row.get("fallback") is True:
        return True
    if row.get("prediction_source") == "rule-fallback":
        return True
    if row.get("model_prediction") is False and row.get("prediction_source") == "rule-fallback":
        return True
    provenance = row.get("stage_provenance") or {}
    if isinstance(provenance, dict):
        for rec in provenance.values():
            if isinstance(rec, dict) and rec.get("status") in {"fallback", "rule-after-fallback"}:
                return True
    return False


def _attention_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {
            "attention_accuracy": None,
            "engage_precision": None,
            "engage_recall": None,
            "drop_precision": None,
            "drop_false_negative_rate": None,
            "denominator": 0,
        }
    correct = 0
    eng_tp = eng_fp = eng_fn = 0
    drop_tp = drop_fp = 0
    important = 0
    important_dropped = 0
    for row in rows:
        gold_states = set((row.get("human_gold") or {}).get("attention_state") or [])
        pred = row.get("attention_state")
        if pred in gold_states:
            correct += 1
        gold_engage = "ENGAGE" in gold_states
        pred_engage = pred == "ENGAGE"
        if pred_engage and gold_engage:
            eng_tp += 1
        elif pred_engage and not gold_engage:
            eng_fp += 1
        elif gold_engage and not pred_engage:
            eng_fn += 1
        gold_drop = gold_states == {"DROP"} or (gold_states and gold_states <= {"DROP"})
        pred_drop = pred == "DROP"
        if pred_drop and gold_drop:
            drop_tp += 1
        elif pred_drop and not gold_drop:
            drop_fp += 1
        is_important = bool(gold_states & {"ENGAGE", "WATCH"})
        if is_important:
            important += 1
            if pred_drop:
                important_dropped += 1
    n = len(rows)
    return {
        "attention_accuracy": correct / n,
        "engage_precision": _div(eng_tp, eng_tp + eng_fp),
        "engage_recall": _div(eng_tp, eng_tp + eng_fn),
        "drop_precision": _div(drop_tp, drop_tp + drop_fp),
        "drop_false_negative_rate": _div(important_dropped, important),
        "denominator": n,
    }


def _kernel_metrics(rows: list[dict]) -> dict:
    must_hit = must_total = 0
    forbidden_hit = forbidden_total = 0
    struct_hit = struct_total = 0
    decision_hit = decision_total = 0
    for row in rows:
        gold = row.get("human_gold") or {}
        matched = set(row.get("matched_kernel_titles") or []) | set(row.get("matched_kernel_ids") or [])
        rels = row.get("match_relevance_types") or []
        for item in gold.get("must_match_kernel") or []:
            must_total += 1
            if item in matched:
                must_hit += 1
        for item in gold.get("forbidden_kernel") or []:
            forbidden_total += 1
            if item in matched:
                forbidden_hit += 1
        if "structural_relevance" in (row.get("cognitive_tasks") or []) or "STRUCTURAL" in rels:
            struct_total += 1
            if "STRUCTURAL" in rels:
                struct_hit += 1
        if "decision_relevance" in (row.get("cognitive_tasks") or []) or "DECISION" in rels:
            decision_total += 1
            if "DECISION" in rels:
                decision_hit += 1
    return {
        "must_match_recall": _div(must_hit, must_total),
        "forbidden_match_rate": _div(forbidden_hit, max(len(rows), 1) if forbidden_total else 0) if forbidden_total else None,
        "structural_relevance_recall": _div(struct_hit, struct_total),
        "decision_relevance_recall": _div(decision_hit, decision_total),
        "must_match_denominator": must_total,
        "forbidden_denominator": forbidden_total,
    }


def _epistemic_metrics(rows: list[dict]) -> dict:
    claim_hit = claim_total = 0
    obs_hit = obs_total = 0
    unsupported_obs = 0
    inf_as_obs = 0
    for row in rows:
        gold = row.get("human_gold") or {}
        claims = [c.lower() for c in (row.get("claim_texts") or [])]
        observations = [o.lower() for o in (row.get("observation_texts") or [])]
        for key in gold.get("key_claims") or []:
            claim_total += 1
            if any(key.lower() in c for c in claims):
                claim_hit += 1
        for key in gold.get("key_observations") or []:
            obs_total += 1
            if any(key.lower() in o for o in observations):
                obs_hit += 1
        unsupported_obs += int(row.get("unsupported_observation_count") or 0)
        inf_as_obs += int(row.get("inference_as_observation_count") or 0)
    n = max(len(rows), 1)
    return {
        "claim_precision": _div(claim_hit, claim_total),
        "observation_precision": _div(obs_hit, obs_total),
        "unsupported_observation_rate": unsupported_obs / n,
        "inference_as_observation_rate": inf_as_obs / n,
    }


def _delta_metrics(rows: list[dict]) -> dict:
    scores = [r.get("delta_rubric") for r in rows if r.get("delta_rubric") is not None]
    return {
        "human_rubric_mean": (sum(scores) / len(scores)) if scores else None,
        "human_rubric_n": len(scores),
        "note": "Model Delta quality is a human rubric 0–3; it is not auto-scored.",
    }


def _safety_metrics(rows: list[dict]) -> dict:
    forbidden = 0
    strong = 0
    n = max(len(rows), 1)
    for row in rows:
        gold = row.get("human_gold") or {}
        blob = " ".join(
            (row.get("delta_summary") or "", " ".join(row.get("inference_texts") or []))
        ).lower()
        for item in gold.get("forbidden_conclusions") or []:
            if item.lower() in blob:
                forbidden += 1
        if row.get("unsupported_strong_conclusion"):
            strong += 1
    return {
        "unsupported_strong_conclusion_rate": strong / n,
        "forbidden_conclusion_rate": forbidden / n,
    }


def _slice(rows: list[dict], key: str) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "unknown")].append(row)
    return {k: {"n": len(v), "attention_accuracy": _attention_metrics(v)["attention_accuracy"]} for k, v in groups.items()}


def _slice_tasks(rows: list[dict]) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        tasks = row.get("cognitive_tasks") or ["unspecified"]
        for task in tasks:
            groups[str(task)].append(row)
    return {k: {"n": len(v), "attention_accuracy": _attention_metrics(v)["attention_accuracy"]} for k, v in groups.items()}


def _div(num: int, den: int) -> float | None:
    if not den:
        return None
    return num / den


def render_markdown(summary: dict) -> str:
    att = summary.get("attention") or {}
    km = summary.get("kernel_matching") or {}
    ep = summary.get("epistemic_separation") or {}
    lines = [
        "# RAOS Live Eval",
        "",
        f"- cases: {summary.get('n_cases')} (labeled {summary.get('n_labeled')}, unlabeled {summary.get('n_unlabeled')})",
        f"- unlabeled excluded from accuracy: {summary.get('unlabeled_excluded_from_accuracy')}",
        f"- fallback cases (not counted as model predictions): {summary.get('n_fallback')}",
        "",
        "## Attention Routing",
        f"- Attention Accuracy: {att.get('attention_accuracy')}",
        f"- ENGAGE Precision: {att.get('engage_precision')}",
        f"- ENGAGE Recall: {att.get('engage_recall')}",
        f"- DROP Precision: {att.get('drop_precision')}",
        f"- DROP False Negative Rate (important → DROP): {att.get('drop_false_negative_rate')}",
        "",
        "## Kernel Matching",
        f"- Must-Match Recall: {km.get('must_match_recall')}",
        f"- Forbidden-Match Rate: {km.get('forbidden_match_rate')}",
        f"- Structural-Relevance Recall: {km.get('structural_relevance_recall')}",
        f"- Decision-Relevance Recall: {km.get('decision_relevance_recall')}",
        "",
        "## Epistemic Separation",
        f"- Claim Precision: {ep.get('claim_precision')}",
        f"- Observation Precision: {ep.get('observation_precision')}",
        f"- Unsupported Observation Rate: {ep.get('unsupported_observation_rate')}",
        f"- Inference-as-Observation Rate: {ep.get('inference_as_observation_rate')}",
        "",
        "## Model Delta",
        f"- {((summary.get('model_delta') or {}).get('note'))}",
        "",
        "## Safety",
        f"- Unsupported Strong Conclusion Rate: {(summary.get('safety') or {}).get('unsupported_strong_conclusion_rate')}",
        f"- Forbidden Conclusion Rate: {(summary.get('safety') or {}).get('forbidden_conclusion_rate')}",
        "",
    ]
    return "\n".join(lines) + "\n"
