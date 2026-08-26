from __future__ import annotations

from collections import defaultdict
from typing import Any

from eval.live.schema import HumanGold, KERNEL_TARGET_NONE


def compute_metrics(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = [r for r in case_rows if r.get("gold_status") == "LABELED"]
    unlabeled_n = sum(1 for r in case_rows if r.get("gold_status") != "LABELED")
    fallback_rows = [r for r in case_rows if _is_rule_fallback(r)]
    model_labeled = [r for r in labeled if not _is_rule_fallback(r)]
    attention = _attention_metrics(model_labeled)
    modes = _processing_mode_metrics(model_labeled)
    kernel = _kernel_metrics(model_labeled)
    effects = _cognitive_effect_metrics(model_labeled)
    expected_delta = _expected_delta_metrics(model_labeled)
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
        "processing_mode": modes,
        "kernel_target": kernel,
        "kernel_matching": kernel,
        "cognitive_effect": effects,
        "expected_delta": expected_delta,
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


def _gold(row: dict) -> dict:
    return row.get("human_gold") or {}


def _gold_model(row: dict) -> HumanGold:
    return HumanGold.model_validate(_gold(row))


def _pred_modes(row: dict) -> set[str]:
    raw = row.get("processing_modes")
    if raw is None:
        raw = row.get("processing_mode")
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {raw} if raw else set()
    return {str(m) for m in raw if m}


def _matched_labels(row: dict) -> list[str]:
    labels = []
    for item in (row.get("matched_kernel_titles") or []) + (row.get("matched_kernel_ids") or []):
        if item:
            labels.append(str(item))
    return labels


def _target_in_matches(target: str, labels: list[str]) -> bool:
    if not target or target.upper() == KERNEL_TARGET_NONE:
        return False
    needle = target.lower()
    for label in labels:
        low = label.lower()
        if needle == low or needle in low or low in needle:
            return True
    return False


def _pred_effect_rows(row: dict) -> list[dict]:
    impact = row.get("cognitive_impact") or {}
    if isinstance(impact, dict):
        return [e for e in (impact.get("effects") or []) if isinstance(e, dict)]
    return []


def _processing_mode_metrics(rows: list[dict]) -> dict:
    scored = 0
    hit = 0
    for row in rows:
        gold_modes = set(_gold_model(row).processing_modes)
        if not gold_modes:
            continue
        scored += 1
        pred = _pred_modes(row)
        if pred and pred <= gold_modes:
            hit += 1
    return {
        "processing_mode_accuracy": _div(hit, scored),
        "denominator": scored,
        "note": "Predicted modes must be a subset of the Human Gold acceptable set.",
    }


def _kernel_metrics(rows: list[dict]) -> dict:
    scored = hit = 0
    none_scored = none_hit = 0
    must_hit = must_total = 0
    forbidden_hit = forbidden_total = 0
    struct_hit = struct_total = 0
    decision_hit = decision_total = 0
    for row in rows:
        gold = _gold_model(row)
        labels = _matched_labels(row)
        targets = [t for t in gold.kernel_targets if t]
        named = [t for t in targets if t.upper() != KERNEL_TARGET_NONE]
        none_only = bool(targets) and not named
        if named:
            scored += 1
            if all(_target_in_matches(t, labels) for t in named):
                hit += 1
        if none_only:
            none_scored += 1
            effects = _pred_effect_rows(row)
            open_untargeted = any(
                (e.get("effect") in {"OPEN_NEW", "NO_MATERIAL_CHANGE"}) and not e.get("target_kernel_node_id")
                for e in effects
            )
            if not labels or open_untargeted:
                none_hit += 1
        rels = row.get("match_relevance_types") or []
        for item in gold.must_match_kernel or []:
            must_total += 1
            if _target_in_matches(item, labels) or item in set(row.get("matched_kernel_ids") or []):
                must_hit += 1
        for item in gold.forbidden_kernel or []:
            forbidden_total += 1
            if _target_in_matches(item, labels):
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
        "kernel_target_accuracy": _div(hit, scored),
        "kernel_target_none_accuracy": _div(none_hit, none_scored),
        "denominator": scored,
        "none_denominator": none_scored,
        "must_match_recall": _div(must_hit, must_total) if must_total else _div(hit, scored),
        "forbidden_match_rate": _div(forbidden_hit, forbidden_total) if forbidden_total else None,
        "structural_relevance_recall": _div(struct_hit, struct_total),
        "decision_relevance_recall": _div(decision_hit, decision_total),
        "must_match_denominator": must_total or scored,
        "forbidden_denominator": forbidden_total,
    }


def _cognitive_effect_metrics(rows: list[dict]) -> dict:
    scored = hit = 0
    for row in rows:
        gold = _gold_model(row)
        pairs = gold.target_effect_pairs()
        kinds_only = [k for k in gold.cognitive_effects if k]
        pairs = [(t, a) for t, a in pairs if a]
        if not pairs and not kinds_only:
            continue
        pred = _pred_effect_rows(row)
        pred_kinds = {str(e.get("effect")) for e in pred if e.get("effect")}
        labels = _matched_labels(row)
        id_to_title = {}
        for match in row.get("kernel_matches") or []:
            if isinstance(match, dict) and match.get("node_id"):
                id_to_title[str(match["node_id"])] = str(match.get("title") or "")
        scored += 1
        ok = True
        if pairs:
            for target, acceptable in pairs:
                if not acceptable:
                    continue
                acceptable_set = {a.upper() for a in acceptable}
                if target.upper() == KERNEL_TARGET_NONE:
                    relevant = [e for e in pred if not e.get("target_kernel_node_id")]
                    if not relevant:
                        relevant = pred
                else:
                    relevant = []
                    for effect in pred:
                        nid = str(effect.get("target_kernel_node_id") or "")
                        title = id_to_title.get(nid, "")
                        if _target_in_matches(target, [title, nid, *labels]):
                            relevant.append(effect)
                    if not relevant:
                        relevant = [e for e in pred if str(e.get("effect") or "").upper() in acceptable_set]
                if not any(str(e.get("effect") or "").upper() in acceptable_set for e in relevant):
                    ok = False
                    break
        elif kinds_only and not (pred_kinds & set(kinds_only)):
            ok = False
        if ok:
            hit += 1
    return {
        "cognitive_effect_accuracy": _div(hit, scored),
        "denominator": scored,
        "note": "Predicted CognitiveEffect kinds must be in the Human Gold acceptable set for the target.",
    }


def _expected_delta_metrics(rows: list[dict]) -> dict:
    labeled = 0
    for row in rows:
        text = (_gold(row).get("expected_delta") or "").strip()
        if text:
            labeled += 1
    return {
        "n_with_expected_delta": labeled,
        "denominator": labeled,
        "auto_scored": False,
        "note": "Expected Delta is free text for human review; it is not auto-scored. See cases.jsonl human_gold.expected_delta.",
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
    modes = summary.get("processing_mode") or {}
    km = summary.get("kernel_target") or summary.get("kernel_matching") or {}
    fx = summary.get("cognitive_effect") or {}
    ed = summary.get("expected_delta") or {}
    ep = summary.get("epistemic_separation") or {}
    lines = [
        "# RAOS Live Eval",
        "",
        f"- cases: {summary.get('n_cases')} (labeled {summary.get('n_labeled')}, unlabeled {summary.get('n_unlabeled')})",
        f"- unlabeled excluded from accuracy: {summary.get('unlabeled_excluded_from_accuracy')}",
        f"- fallback cases (not counted as model predictions): {summary.get('n_fallback')}",
        "",
        "## Attention",
        f"- Attention Accuracy: {att.get('attention_accuracy')}",
        f"- ENGAGE Precision: {att.get('engage_precision')}",
        f"- ENGAGE Recall: {att.get('engage_recall')}",
        f"- DROP Precision: {att.get('drop_precision')}",
        f"- DROP False Negative Rate (important → DROP): {att.get('drop_false_negative_rate')}",
        "",
        "## Processing Mode",
        f"- Processing Mode Accuracy: {modes.get('processing_mode_accuracy')}",
        f"- {modes.get('note')}",
        "",
        "## Kernel Target",
        f"- Kernel Target Accuracy: {km.get('kernel_target_accuracy')}",
        f"- Kernel Target NONE Accuracy: {km.get('kernel_target_none_accuracy')}",
        "",
        "## Cognitive Effect",
        f"- Cognitive Effect Accuracy: {fx.get('cognitive_effect_accuracy')}",
        f"- {fx.get('note')}",
        "",
        "## Expected Delta",
        f"- cases with Expected Delta text: {ed.get('n_with_expected_delta')}",
        f"- {ed.get('note')}",
        "",
        "## Legacy diagnostics (optional gold only)",
        f"- Must-Match Recall: {km.get('must_match_recall')}",
        f"- Forbidden-Match Rate: {km.get('forbidden_match_rate')}",
        f"- Claim Precision: {ep.get('claim_precision')}",
        f"- Observation Precision: {ep.get('observation_precision')}",
        f"- Unsupported Observation Rate: {ep.get('unsupported_observation_rate')}",
        f"- Inference-as-Observation Rate: {ep.get('inference_as_observation_rate')}",
        f"- {(summary.get('model_delta') or {}).get('note')}",
        f"- Unsupported Strong Conclusion Rate: {(summary.get('safety') or {}).get('unsupported_strong_conclusion_rate')}",
        f"- Forbidden Conclusion Rate: {(summary.get('safety') or {}).get('forbidden_conclusion_rate')}",
        "",
    ]
    return "\n".join(lines) + "\n"
