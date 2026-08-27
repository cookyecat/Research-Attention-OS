from __future__ import annotations

from collections import defaultdict
from typing import Any

from eval.live.kernel_snapshot import resolve_snapshot_node_id, snapshot_node_by_id
from eval.live.schema import UPDATE_OPERATIONS, HumanGold


def compute_metrics(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = [r for r in case_rows if r.get("gold_status") == "LABELED"]
    unlabeled_n = sum(1 for r in case_rows if r.get("gold_status") != "LABELED")
    fallback_rows = [r for r in case_rows if _is_rule_fallback(r)]
    model_labeled = [r for r in labeled if not _is_rule_fallback(r)]
    disposition = _disposition_metrics(model_labeled)
    operation = _update_operation_metrics(model_labeled)
    target = _target_metrics(model_labeled)
    delta_content = _delta_content_metrics(model_labeled)
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
        "disposition": disposition,
        "update_operation": operation,
        "target": target,
        "delta_content": delta_content,
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


def _gold(row: dict) -> dict:
    return row.get("human_gold") or {}


def _gold_model(row: dict) -> HumanGold:
    return HumanGold.model_validate(_gold(row))


def _pred_disposition(row: dict) -> str | None:
    if row.get("disposition"):
        return row.get("disposition")
    plan = row.get("attention_plan") or {}
    if isinstance(plan, dict) and plan.get("disposition"):
        return plan.get("disposition")
    return None


def _pred_effect_rows(row: dict) -> list[dict]:
    impact = row.get("cognitive_impact") or {}
    if isinstance(impact, dict):
        return [e for e in (impact.get("effects") or []) if isinstance(e, dict)]
    return []


def _pred_operation_of(item: dict) -> str | None:
    raw = item.get("operation")
    if raw is None:
        return None
    value = str(raw).upper()
    return value if value in UPDATE_OPERATIONS else None


def _pred_updates(row: dict) -> list[tuple[str, str | None]]:
    upd = row.get("update")
    if isinstance(upd, dict) and upd.get("operation"):
        op = str(upd["operation"]).upper()
        if op in UPDATE_OPERATIONS:
            nid = upd.get("target_node_id")
            return [(op, str(nid) if nid else None)]
    updates: list[tuple[str, str | None]] = []
    for effect in _pred_effect_rows(row):
        op = _pred_operation_of(effect)
        if not op:
            continue
        nid = effect.get("target_kernel_node_id")
        updates.append((op, str(nid) if nid else None))
    return updates


def _id_to_title(row: dict) -> dict[str, str]:
    """UUID → title directory from the Kernel Snapshot matches. Not a hit signal."""
    mapping: dict[str, str] = {}
    for match in row.get("kernel_matches") or []:
        if isinstance(match, dict) and match.get("node_id"):
            mapping[str(match["node_id"])] = str(match.get("title") or "")
    ids = row.get("matched_kernel_ids") or []
    titles = row.get("matched_kernel_titles") or []
    for nid, title in zip(ids, titles):
        if nid and title:
            mapping.setdefault(str(nid), str(title))
    return mapping


def _resolve_pred_target(nid: str | None, id_to_title: dict[str, str]) -> str | None:
    if not nid:
        return None
    if snapshot_node_by_id(nid) is not None:
        return nid
    title = id_to_title.get(nid)
    if title:
        resolved = resolve_snapshot_node_id(title)
        if resolved and snapshot_node_by_id(resolved) is not None:
            return resolved
    resolved = resolve_snapshot_node_id(nid)
    if resolved and snapshot_node_by_id(resolved) is not None:
        return resolved
    return nid


def _resolved_pred_targets(row: dict) -> list[str | None]:
    lookup = _id_to_title(row)
    return [_resolve_pred_target(nid, lookup) for _, nid in _pred_updates(row)]


def _disposition_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {
            "disposition_accuracy": None,
            "engage_precision": None,
            "engage_recall": None,
            "drop_precision": None,
            "drop_false_negative_rate": None,
            "denominator": 0,
        }
    scored = hit = 0
    eng_tp = eng_fp = eng_fn = 0
    drop_tp = drop_fp = 0
    important = 0
    important_dropped = 0
    for row in rows:
        gold = _gold_model(row).disposition
        if not gold:
            continue
        scored += 1
        pred = _pred_disposition(row)
        if pred == gold:
            hit += 1
        gold_engage = gold == "ENGAGE"
        pred_engage = pred == "ENGAGE"
        if pred_engage and gold_engage:
            eng_tp += 1
        elif pred_engage and not gold_engage:
            eng_fp += 1
        elif gold_engage and not pred_engage:
            eng_fn += 1
        gold_drop = gold == "DROP"
        pred_drop = pred == "DROP"
        if pred_drop and gold_drop:
            drop_tp += 1
        elif pred_drop and not gold_drop:
            drop_fp += 1
        if gold in {"ENGAGE", "WATCH"}:
            important += 1
            if pred_drop:
                important_dropped += 1
    return {
        "disposition_accuracy": _div(hit, scored),
        "engage_precision": _div(eng_tp, eng_tp + eng_fp),
        "engage_recall": _div(eng_tp, eng_tp + eng_fn),
        "drop_precision": _div(drop_tp, drop_tp + drop_fp),
        "drop_false_negative_rate": _div(important_dropped, important),
        "denominator": scored,
    }


def _update_operation_metrics(rows: list[dict]) -> dict:
    scored = hit = 0
    for row in rows:
        gold = _gold_model(row)
        op = gold.update.operation if gold.update else None
        if not op:
            continue
        scored += 1
        pred_ops = {item[0] for item in _pred_updates(row)}
        if op in pred_ops:
            hit += 1
    return {
        "update_operation_accuracy": _div(hit, scored),
        "denominator": scored,
        "note": "Predicted update.operation is scored directly against REINFORCE | CHALLENGE | OPEN_NEW.",
    }


def _target_metrics(rows: list[dict]) -> dict:
    scored = hit = 0
    for row in rows:
        gold = _gold_model(row)
        update = gold.update
        if not update or not update.operation:
            continue
        scored += 1
        pred_targets = _resolved_pred_targets(row)
        if update.operation == "OPEN_NEW":
            if all(t is None for t in pred_targets):
                hit += 1
            continue
        if update.target_node_id and update.target_node_id in {t for t in pred_targets if t}:
            hit += 1
    return {
        "target_accuracy": _div(hit, scored),
        "denominator": scored,
        "note": "Target is the predicted update's Kernel Snapshot node, not a retrieval/topic hit.",
    }


def _delta_content_metrics(rows: list[dict]) -> dict:
    labeled = 0
    for row in rows:
        gold = _gold_model(row)
        text = (gold.delta_content or "").strip()
        if text:
            labeled += 1
    return {
        "n_with_delta_content": labeled,
        "denominator": labeled,
        "auto_scored": False,
        "note": "DeltaContent is free text for human review; it is not auto-scored. See cases.jsonl human_gold.delta_content.",
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
    return {k: {"n": len(v), "disposition_accuracy": _disposition_metrics(v)["disposition_accuracy"]} for k, v in groups.items()}


def _slice_tasks(rows: list[dict]) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        tasks = row.get("cognitive_tasks") or ["unspecified"]
        for task in tasks:
            groups[str(task)].append(row)
    return {k: {"n": len(v), "disposition_accuracy": _disposition_metrics(v)["disposition_accuracy"]} for k, v in groups.items()}


def _div(num: int, den: int) -> float | None:
    if not den:
        return None
    return num / den


def render_markdown(summary: dict) -> str:
    disp = summary.get("disposition") or {}
    op = summary.get("update_operation") or {}
    target = summary.get("target") or {}
    dc = summary.get("delta_content") or {}
    ep = summary.get("epistemic_separation") or {}
    lines = [
        "# RAOS Live Eval",
        "",
        f"- cases: {summary.get('n_cases')} (labeled {summary.get('n_labeled')}, unlabeled {summary.get('n_unlabeled')})",
        f"- unlabeled excluded from accuracy: {summary.get('unlabeled_excluded_from_accuracy')}",
        f"- fallback cases (not counted as model predictions): {summary.get('n_fallback')}",
        "",
        "## Disposition",
        f"- Disposition Accuracy: {disp.get('disposition_accuracy')}",
        f"- ENGAGE Precision: {disp.get('engage_precision')}",
        f"- ENGAGE Recall: {disp.get('engage_recall')}",
        f"- DROP Precision: {disp.get('drop_precision')}",
        f"- DROP False Negative Rate (important → DROP): {disp.get('drop_false_negative_rate')}",
        "",
        "## Update Operation",
        f"- Update Operation Accuracy: {op.get('update_operation_accuracy')}",
        f"- {op.get('note')}",
        "",
        "## Target",
        f"- Target Accuracy: {target.get('target_accuracy')}",
        f"- {target.get('note')}",
        "",
        "## Delta Content",
        f"- cases with Delta Content text: {dc.get('n_with_delta_content')}",
        f"- {dc.get('note')}",
        "",
        "## Legacy diagnostics (optional gold only)",
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
