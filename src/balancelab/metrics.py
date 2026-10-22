"""Solution representation, feasibility verification and balance metrics."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from .model import Problem

EPS = 1e-9


@dataclass
class Solution:
    method: str
    stations: List[List[str]]  # task ids per station, in execution order
    status: str = "feasible"   # "feasible" | "infeasible" | "unavailable"
    note: str = ""

    # filled by evaluate()
    loads: List[float] = field(default_factory=list)
    total_time: float = 0.0
    takt: float = 0.0
    efficiency: float = 0.0        # total_time / (n_stations * takt)
    balance_delay: float = 0.0     # 1 - efficiency
    smoothness_index: float = 0.0  # sqrt(sum((max_load - load_i)^2))
    bottleneck_station: int = -1   # 0-based index of the fullest station
    bottleneck_load: float = 0.0
    idle_times: List[float] = field(default_factory=list)
    total_idle: float = 0.0

    @property
    def n_stations(self) -> int:
        return len(self.stations)

    def assignment(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for idx, station in enumerate(self.stations):
            for tid in station:
                out[tid] = idx
        return out


def verify(problem: Problem, stations: List[List[str]]) -> List[str]:
    """Return a list of feasibility violations (empty list means feasible).

    Checks: every task assigned exactly once; for every precedence pair the
    predecessor's station index is <= the successor's; no station load
    exceeds the takt.
    """
    problems: List[str] = []
    assign: Dict[str, int] = {}
    for idx, station in enumerate(stations):
        for tid in station:
            if tid in assign:
                problems.append("task %s assigned more than once" % tid)
            assign[tid] = idx
    for t in problem.tasks:
        if t.id not in assign:
            problems.append("task %s is not assigned" % t.id)
    for t in problem.tasks:
        for p in t.predecessors:
            if p in assign and t.id in assign and assign[p] > assign[t.id]:
                problems.append(
                    "precedence violated: %s (station %d) after %s (station %d)"
                    % (p, assign[p], t.id, assign[t.id])
                )
    takt = problem.require_takt()
    for idx, station in enumerate(stations):
        load = sum(problem.task(tid).time for tid in station)
        if load > takt + 1e-6:
            problems.append(
                "station %d load %.4f exceeds takt %.4f" % (idx + 1, load, takt)
            )
    return problems


def evaluate(problem: Problem, solution: Solution) -> Solution:
    """Compute loads and balance metrics in place and return the solution."""
    takt = problem.require_takt()
    loads = [
        float(sum(problem.task(tid).time for tid in station))
        for station in solution.stations
    ]
    solution.loads = loads
    solution.takt = takt
    solution.total_time = problem.total_time
    n = len(loads)
    if n == 0:
        solution.status = "infeasible"
        return solution
    arr = np.asarray(loads, dtype=float)
    solution.efficiency = problem.total_time / (n * takt)
    solution.balance_delay = 1.0 - solution.efficiency
    max_load = float(arr.max())
    solution.smoothness_index = float(
        math.sqrt(float(np.sum((max_load - arr) ** 2)))
    )
    solution.bottleneck_station = int(arr.argmax())
    solution.bottleneck_load = max_load
    solution.idle_times = [takt - load for load in loads]
    solution.total_idle = float(sum(solution.idle_times))
    return solution
