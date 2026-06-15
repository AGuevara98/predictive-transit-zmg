# src/w5_pareto.py
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from src.w5_types import ObjectiveResult


def pareto_objectives(results: List[ObjectiveResult]) -> np.ndarray:
    """Return (n, 3) matrix of objectives to MINIMIZE: (-f1, f2, -f3)."""
    return np.array(
        [[-r.f1_demand_gain, r.f2_route_km, -r.f3_equity] for r in results],
        dtype=float,
    )


def dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """True if vector a weakly dominates b on all objectives and strictly on at least one."""
    return bool(np.all(a <= b) and np.any(a < b))


def pareto_rank(results: List[ObjectiveResult]) -> np.ndarray:
    """Fast non-dominated sort; rank 1 = Pareto front (best), higher = more dominated."""
    n = len(results)
    if n == 0:
        return np.array([], dtype=int)

    obj = pareto_objectives(results)
    ranks = np.zeros(n, dtype=int)
    dominated_count = np.zeros(n, dtype=int)
    domination_sets: List[List[int]] = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if dominates(obj[i], obj[j]):
                domination_sets[i].append(j)
            elif dominates(obj[j], obj[i]):
                dominated_count[i] += 1

    current_front = [i for i in range(n) if dominated_count[i] == 0]
    rank = 1
    while current_front:
        for i in current_front:
            ranks[i] = rank
        next_front: List[int] = []
        for i in current_front:
            for j in domination_sets[i]:
                dominated_count[j] -= 1
                if dominated_count[j] == 0:
                    next_front.append(j)
        current_front = next_front
        rank += 1

    return ranks
