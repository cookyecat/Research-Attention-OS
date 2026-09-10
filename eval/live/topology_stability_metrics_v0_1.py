from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Hashable, Iterable, Sequence

VERSION = "topology-stability-metrics-v0.1"

Topology = tuple[Hashable, ...]


def canonical_topology(relations: Iterable[Hashable]) -> Topology:
    """Canonical set-valued topology. Duplicate identical relations are not extra topology."""
    return tuple(sorted(set(relations), key=repr))


def jaccard(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    aa, bb = set(a), set(b)
    if not aa and not bb:
        return 1.0
    return len(aa & bb) / len(aa | bb)


def mean_pairwise_jaccard(topologies: Sequence[Sequence[Hashable]]) -> float:
    if not topologies:
        return 0.0
    if len(topologies) == 1:
        return 1.0
    values = [
        jaccard(topologies[i], topologies[j])
        for i in range(len(topologies))
        for j in range(i + 1, len(topologies))
    ]
    return sum(values) / len(values)


def topology_entropy_bits(topologies: Sequence[Topology]) -> float:
    if not topologies:
        return 0.0
    counts = Counter(topologies)
    n = len(topologies)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def exact_topology_mode_rate(topologies: Sequence[Topology]) -> float:
    if not topologies:
        return 0.0
    counts = Counter(topologies)
    return max(counts.values()) / len(topologies)


def relation_frequency(topologies: Sequence[Topology]) -> dict[Hashable, float]:
    if not topologies:
        return {}
    counts = Counter(r for topology in topologies for r in set(topology))
    return {relation: count / len(topologies) for relation, count in counts.items()}


def critical_relation_recall(topologies: Sequence[Topology], critical: Iterable[Hashable]) -> dict[Hashable, float]:
    frequencies = relation_frequency(topologies)
    return {relation: frequencies.get(relation, 0.0) for relation in critical}


def categorical_stability(values: Sequence[Hashable]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    return max(counts.values()) / len(values)


def instability_from_mode_rate(mode_rate: float) -> float:
    """Unitless descriptive instability in [0,1], not Euclidean variance."""
    return 1.0 - float(mode_rate)


@dataclass(frozen=True)
class TopologyStabilityReport:
    n: int
    n_unique: int
    exact_mode_rate: float
    mean_pairwise_jaccard: float
    entropy_bits: float
    relation_frequency: dict[Hashable, float]
    critical_relation_recall: dict[Hashable, float]

    @property
    def descriptive_instability(self) -> float:
        return instability_from_mode_rate(self.exact_mode_rate)

    def as_dict(self) -> dict:
        return {
            "version": VERSION,
            "n": self.n,
            "n_unique": self.n_unique,
            "exact_mode_rate": self.exact_mode_rate,
            "mean_pairwise_jaccard": self.mean_pairwise_jaccard,
            "entropy_bits": self.entropy_bits,
            "relation_frequency": {str(k): v for k, v in self.relation_frequency.items()},
            "critical_relation_recall": {str(k): v for k, v in self.critical_relation_recall.items()},
            "descriptive_instability": self.descriptive_instability,
        }


def summarize_topology_stability(
    topologies: Sequence[Iterable[Hashable]],
    *,
    critical_relations: Iterable[Hashable] = (),
) -> TopologyStabilityReport:
    canonical = [canonical_topology(t) for t in topologies]
    return TopologyStabilityReport(
        n=len(canonical),
        n_unique=len(set(canonical)),
        exact_mode_rate=exact_topology_mode_rate(canonical),
        mean_pairwise_jaccard=mean_pairwise_jaccard(canonical),
        entropy_bits=topology_entropy_bits(canonical),
        relation_frequency=relation_frequency(canonical),
        critical_relation_recall=critical_relation_recall(canonical, critical_relations),
    )


def execution_snapshot() -> dict:
    return {
        "version": VERSION,
        "topology_semantics": "set-of-decision-relations",
        "metric_priority": [
            "critical_relation_recall",
            "exact_topology_mode_rate",
            "mean_pairwise_jaccard",
            "topology_entropy_bits",
        ],
        "variance_guardrail": "descriptive-discrete-instability-not-euclidean-anova",
    }
