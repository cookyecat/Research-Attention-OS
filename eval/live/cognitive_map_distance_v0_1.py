from __future__ import annotations

from collections import Counter
import math
from typing import Hashable, Sequence

VERSION = "cognitive-map-distance-v0.1"


def _prob_from_counts(counts: Counter, n: int) -> dict[Hashable, float]:
    if n <= 0:
        return {}
    return {k: v / n for k, v in counts.items() if v}


def js_divergence_bits(p: dict[Hashable, float], q: dict[Hashable, float]) -> float:
    keys = set(p) | set(q)
    if not keys:
        return 0.0
    m = {k: (p.get(k, 0.0) + q.get(k, 0.0)) / 2.0 for k in keys}
    def kl(a, b):
        total = 0.0
        for k, av in a.items():
            if av > 0:
                total += av * math.log2(av / b[k])
        return total
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def _freeze(value):
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v)) for k, v in value.items()))
    return value


def canonical_state(items) -> tuple:
    return tuple(sorted({_freeze(v) for v in (items or ())}, key=repr))


def empirical_state_distribution(samples: Sequence[dict], field: str) -> dict:
    states = []
    for s in samples:
        if field == "load_bearing":
            state = canonical_state(list(s.get("necessary_core") or ()) + list(s.get("sufficient_supports") or ()))
        else:
            state = canonical_state(s.get(field) or ())
        states.append(state)
    return _prob_from_counts(Counter(states), len(states))


def attention_distribution(samples: Sequence[dict]) -> dict:
    return _prob_from_counts(Counter(str(s.get("attention") or "") for s in samples), len(samples))


def frequency_drift(map0: dict, map1: dict, field: str) -> dict:
    r0 = map0.get("relation_map") or {}
    r1 = map1.get("relation_map") or {}
    keys = sorted(set(r0) | set(r1))
    rows = []
    for key in keys:
        p0 = float(((r0.get(key) or {}).get(field) or {}).get("p", 0.0))
        p1 = float(((r1.get(key) or {}).get(field) or {}).get("p", 0.0))
        rows.append({"relation": key, "p_t0": p0, "p_t1": p1, "delta": p1 - p0, "abs_delta": abs(p1 - p0)})
    return {
        "n_relations": len(rows),
        "mean_abs_delta": sum(r["abs_delta"] for r in rows) / len(rows) if rows else 0.0,
        "max_abs_delta": max((r["abs_delta"] for r in rows), default=0.0),
        "top_changes": sorted(rows, key=lambda r: (-r["abs_delta"], r["relation"]))[:10],
    }


def compare_cognitive_maps(map0: dict, samples0: Sequence[dict], map1: dict, samples1: Sequence[dict]) -> dict:
    att0, att1 = attention_distribution(samples0), attention_distribution(samples1)
    top0, top1 = empirical_state_distribution(samples0, "topology"), empirical_state_distribution(samples1, "topology")
    core0, core1 = empirical_state_distribution(samples0, "load_bearing"), empirical_state_distribution(samples1, "load_bearing")
    return {
        "version": VERSION,
        "n_t0": len(samples0),
        "n_t1": len(samples1),
        "attention_js_bits": js_divergence_bits(att0, att1),
        "topology_state_js_bits": js_divergence_bits(top0, top1),
        "load_bearing_state_js_bits": js_divergence_bits(core0, core1),
        "attention_t0": {str(k): v for k, v in sorted(att0.items(), key=lambda kv: str(kv[0]))},
        "attention_t1": {str(k): v for k, v in sorted(att1.items(), key=lambda kv: str(kv[0]))},
        "topology_relation_frequency_drift": frequency_drift(map0, map1, "topology"),
        "load_bearing_relation_frequency_drift": frequency_drift(map0, map1, "load_bearing"),
        "guardrail": "descriptive empirical cross-epoch distance; not a causal attribution to provider/model drift",
    }


def execution_snapshot() -> dict:
    return {
        "version": VERSION,
        "distances": ["attention-js-bits", "topology-state-js-bits", "load-bearing-state-js-bits", "relation-frequency-drift"],
        "js_range_bits": [0.0, 1.0],
        "temporal_process_model": False,
    }
