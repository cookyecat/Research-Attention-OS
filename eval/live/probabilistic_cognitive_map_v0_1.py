from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Hashable, Iterable, Sequence

VERSION = "static-probabilistic-cognitive-map-v0.1"


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    zz = z * z
    denom = 1.0 + zz / n
    center = (p + zz / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) / n) + zz / (4.0 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def entropy_bits_from_counts(counts: Counter, n: int) -> float:
    if n <= 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


def _canon(relations: Iterable[Hashable]) -> tuple[Hashable, ...]:
    return tuple(sorted(set(relations), key=repr))


def _interval_row(count: int, n: int) -> dict:
    lo, hi = wilson_interval(count, n)
    return {"count": count, "p": count / n if n else 0.0, "wilson95": [lo, hi], "half_width": (hi - lo) / 2.0}


def summarize_static_cognitive_map(samples: Sequence[dict]) -> dict:
    n = len(samples)
    topology_sets = [_canon(s.get("topology") or ()) for s in samples]
    necessary_sets = [_canon(s.get("necessary_core") or ()) for s in samples]
    sufficient_sets = [_canon(s.get("sufficient_supports") or ()) for s in samples]
    load_bearing_sets = [_canon(set(necessary_sets[i]) | set(sufficient_sets[i])) for i in range(n)]
    attentions = [str(s.get("attention") or "") for s in samples]

    universe = sorted(
        set(r for ts in topology_sets for r in ts) | set(r for bs in load_bearing_sets for r in bs),
        key=repr,
    )
    relation_rows = {}
    for rel in universe:
        present = sum(rel in ts for ts in topology_sets)
        necessary = sum(rel in cs for cs in necessary_sets)
        sufficient = sum(rel in ss for ss in sufficient_sets)
        load = sum(rel in bs for bs in load_bearing_sets)
        relation_rows[repr(rel)] = {
            "relation": rel,
            "topology": _interval_row(present, n),
            "necessary": _interval_row(necessary, n),
            "sufficient": _interval_row(sufficient, n),
            "load_bearing": _interval_row(load, n),
            "load_bearing_given_present": _interval_row(load, present) if present else _interval_row(0, 0),
        }

    att_counts = Counter(attentions)
    att_probs = {k: _interval_row(v, n) for k, v in sorted(att_counts.items())}
    dominant = None
    if att_counts:
        dominant = sorted(att_counts, key=lambda k: (-att_counts[k], k))[0]
    topology_counts = Counter(topology_sets)
    core_counts = Counter(load_bearing_sets)

    return {
        "version": VERSION,
        "n": n,
        "relation_map": relation_rows,
        "topology_distribution": {
            "n_unique": len(topology_counts),
            "mode_rate": max(topology_counts.values()) / n if n else 0.0,
            "entropy_bits": entropy_bits_from_counts(topology_counts, n),
        },
        "load_bearing_distribution": {
            "n_unique": len(core_counts),
            "mode_rate": max(core_counts.values()) / n if n else 0.0,
            "entropy_bits": entropy_bits_from_counts(core_counts, n),
        },
        "attention_distribution": {
            "counts": dict(sorted(att_counts.items())),
            "probabilities": att_probs,
            "entropy_bits": entropy_bits_from_counts(att_counts, n),
            "normalized_entropy": entropy_bits_from_counts(att_counts, n) / 2.0 if n else 0.0,
            "dominant_action": dominant,
            "concentration": att_counts[dominant] / n if dominant and n else 0.0,
            "dominant_wilson95": list(wilson_interval(att_counts[dominant], n)) if dominant and n else [0.0, 0.0],
        },
        "semantics": {
            "topology_probability": "P(r in T)",
            "necessary_probability": "P(r in N_pi(T))",
            "sufficient_probability": "P(r in S_pi(T))",
            "load_bearing_probability": "P(r in B_pi(T)), B_pi=N_pi union S_pi",
            "attention_probability": "P(A)",
            "guardrail": "empirical bounded-epoch distribution; not a stochastic-process model",
        },
    }


def execution_snapshot() -> dict:
    return {
        "version": VERSION,
        "map": ["P(r in T)", "P(r in B_pi(T))", "P(A)"],
        "core_definition": "B_pi(T)=necessary_core union sufficient_supports",
        "interval": "wilson-95",
        "attention_entropy": "shannon-bits; normalized by log2(4)=2",
        "temporal_model": False,
    }
