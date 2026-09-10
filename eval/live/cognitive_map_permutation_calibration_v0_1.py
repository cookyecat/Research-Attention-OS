from __future__ import annotations

import random
from typing import Callable, Sequence

VERSION = "cognitive-map-permutation-null-v0.1"


def permutation_calibrate(
    samples0: Sequence[dict],
    samples1: Sequence[dict],
    *,
    statistic: Callable[[Sequence[dict], Sequence[dict]], float],
    permutations: int = 5000,
    seed: int = 20260910,
) -> dict:
    n0 = len(samples0)
    pooled = list(samples0) + list(samples1)
    if n0 <= 0 or n0 >= len(pooled):
        raise ValueError("both groups must be non-empty")
    observed = float(statistic(samples0, samples1))
    rng = random.Random(seed)
    null = []
    idx = list(range(len(pooled)))
    for _ in range(permutations):
        rng.shuffle(idx)
        left_idx = set(idx[:n0])
        a = [pooled[i] for i in range(len(pooled)) if i in left_idx]
        b = [pooled[i] for i in range(len(pooled)) if i not in left_idx]
        null.append(float(statistic(a, b)))
    null_sorted = sorted(null)
    def q(frac: float) -> float:
        if not null_sorted: return 0.0
        pos = min(len(null_sorted)-1, max(0, int(round(frac*(len(null_sorted)-1)))))
        return null_sorted[pos]
    ge = sum(x >= observed - 1e-15 for x in null)
    p = (ge + 1) / (permutations + 1)
    return {
        "version": VERSION,
        "observed": observed,
        "permutations": permutations,
        "seed": seed,
        "null_median": q(.5),
        "null_p95": q(.95),
        "null_p99": q(.99),
        "tail_probability": p,
        "exceeds_null_p95": observed > q(.95) + 1e-15,
        "drift_supported_v0_1": observed > q(.95) + 1e-15 and p <= .05,
        "guardrail": "Monte Carlo permutation calibration assumes exchangeability under the no-epoch-shift null; descriptive research gate, not a calibrated causal test",
    }


def execution_snapshot() -> dict:
    return {
        "version": VERSION,
        "default_permutations": 5000,
        "default_seed": 20260910,
        "gate": "observed>null_p95 and tail_probability<=0.05",
        "causal_attribution": False,
    }
