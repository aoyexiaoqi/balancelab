"""Solvers for the single-model assembly line balancing problem (SALBP-1).

* ``solve_greedy``  -- ranked positional weight (RPW) heuristic.
* ``solve_local``   -- local-search improvement on top of the greedy result
  (single-task moves and pairwise swaps, precedence always respected).
* ``solve_cpsat``   -- exact CP-SAT model; only available when the optional
  ``ortools`` package is installed.  The core package never imports it.

Every solver returns an evaluated :class:`~balancelab.metrics.Solution` and
never violates precedence or the takt (infeasibility is raised/reported,
never silently produced).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from .metrics import Solution, evaluate, verify
from .model import InfeasibleError, Problem

EPS = 1e-9


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def topo_order(problem: Problem) -> List[str]:
    """A topological ordering of task ids (stable w.r.t. input order)."""
    succ = problem.successors()
    indeg = {t.id: len(t.predecessors) for t in problem.tasks}
    order: List[str] = []
    ready = [t.id for t in problem.tasks if indeg[t.id] == 0]
    while ready:
        cur = ready.pop(0)
        order.append(cur)
        for nxt in succ[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
    return order


def positional_weights(problem: Problem) -> Dict[str, float]:
    """RPW: own time plus the times of all transitive successors."""
    weights: Dict[str, float] = {}
    for t in problem.tasks:
        desc = problem.descendants(t.id)
        weights[t.id] = t.time + sum(problem.task(d).time for d in desc)
    return weights


def _stations_from_assignment(
    problem: Problem, assign: Dict[str, int]
) -> List[List[str]]:
    order = topo_order(problem)
    rank = {tid: i for i, tid in enumerate(order)}
    slots: Dict[int, List[str]] = {}
    for tid, s in assign.items():
        slots.setdefault(s, []).append(tid)
    return [
        sorted(slots[s], key=lambda tid: rank[tid]) for s in sorted(slots)
    ]


# ---------------------------------------------------------------------------
# greedy (ranked positional weight)
# ---------------------------------------------------------------------------

def solve_greedy(problem: Problem) -> Solution:
    problem.check_task_times()
    takt = problem.require_takt()
    weights = positional_weights(problem)
    assigned: Dict[str, int] = {}
    unassigned = set(problem.ids)
    stations: List[List[str]] = []
    while unassigned:
        station: List[str] = []
        load = 0.0
        while True:
            eligible = [
                tid
                for tid in unassigned
                if all(p in assigned for p in problem.task(tid).predecessors)
            ]
            fitting = [
                tid
                for tid in eligible
                if problem.task(tid).time <= takt - load + EPS
            ]
            if not fitting:
                break
            pick = sorted(fitting, key=lambda tid: (-weights[tid], tid))[0]
            station.append(pick)
            assigned[pick] = len(stations)
            unassigned.discard(pick)
            load += problem.task(pick).time
        if not station:  # pragma: no cover - guarded by check_task_times
            raise InfeasibleError("greedy could not place remaining tasks")
        stations.append(station)
    # present each station's tasks in topological (execution) order
    rank = {tid: i for i, tid in enumerate(topo_order(problem))}
    stations = [sorted(st, key=lambda tid: rank[tid]) for st in stations]
    sol = Solution(method="greedy-rpw", stations=stations)
    bad = verify(problem, stations)
    if bad:  # pragma: no cover - defensive
        raise InfeasibleError("greedy produced infeasible solution: %s" % bad)
    return evaluate(problem, sol)


# ---------------------------------------------------------------------------
# local search improvement
# ---------------------------------------------------------------------------

def _objective(problem: Problem, assign: Dict[str, int]):
    stations = _stations_from_assignment(problem, assign)
    loads = [
        sum(problem.task(tid).time for tid in st) for st in stations
    ]
    if not loads:
        return (0, 0.0)
    top = max(loads)
    smooth = math.sqrt(sum((top - load) ** 2 for load in loads))
    return (len(stations), smooth)


def _slot_bounds(
    problem: Problem, assign: Dict[str, int], tid: str
) -> (int, int):
    """Feasible station-index window for moving ``tid`` (precedence only)."""
    lo = 0
    hi = max(assign.values()) if assign else 0
    for p in problem.task(tid).predecessors:
        lo = max(lo, assign[p])
    succ = problem.successors()
    for s in succ[tid]:
        hi = min(hi, assign[s])
    return lo, hi


def solve_local(
    problem: Problem, start: Optional[Solution] = None, max_passes: int = 200
) -> Solution:
    base = start if start is not None else solve_greedy(problem)
    takt = problem.require_takt()
    times = {t.id: t.time for t in problem.tasks}
    ancestors = {t.id: _ancestors(problem, t.id) for t in problem.tasks}

    assign = base.assignment()

    def slot_loads(a: Dict[str, int]) -> Dict[int, float]:
        loads: Dict[int, float] = {}
        for tid, s in a.items():
            loads[s] = loads.get(s, 0.0) + times[tid]
        return loads

    best_obj = _objective(problem, assign)
    for _ in range(max_passes):
        improved = False
        loads = slot_loads(assign)
        # -- single-task moves -------------------------------------------
        for tid in topo_order(problem):
            cur = assign[tid]
            lo, hi = _slot_bounds(problem, assign, tid)
            for target in range(lo, hi + 1):
                if target == cur:
                    continue
                if loads.get(target, 0.0) + times[tid] > takt + EPS:
                    continue
                trial = dict(assign)
                trial[tid] = target
                obj = _objective(problem, trial)
                if obj < (best_obj[0], best_obj[1] - 1e-9):
                    assign = trial
                    best_obj = obj
                    loads = slot_loads(assign)
                    improved = True
                    break
            # continue scanning other tasks after a successful move
        # -- pairwise swaps ----------------------------------------------
        ids = topo_order(problem)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                sa, sb = assign[a], assign[b]
                if sa == sb:
                    continue
                if b in ancestors[a] or a in ancestors[b]:
                    continue
                lo_a, hi_a = _slot_bounds(problem, assign, a)
                lo_b, hi_b = _slot_bounds(problem, assign, b)
                if not (lo_a <= sb <= hi_a and lo_b <= sa <= hi_b):
                    continue
                la = loads.get(sa, 0.0) - times[a] + times[b]
                lb = loads.get(sb, 0.0) - times[b] + times[a]
                if la > takt + EPS or lb > takt + EPS:
                    continue
                trial = dict(assign)
                trial[a], trial[b] = sb, sa
                obj = _objective(problem, trial)
                if obj < (best_obj[0], best_obj[1] - 1e-9):
                    assign = trial
                    best_obj = obj
                    loads = slot_loads(assign)
                    improved = True
        if not improved:
            break
    stations = _stations_from_assignment(problem, assign)
    sol = Solution(method="local-search", stations=stations)
    bad = verify(problem, stations)
    if bad:  # pragma: no cover - defensive
        raise InfeasibleError("local search broke feasibility: %s" % bad)
    return evaluate(problem, sol)


def _ancestors(problem: Problem, tid: str) -> set:
    seen = set()
    stack = list(problem.task(tid).predecessors)
    while stack:
        cur = stack.pop()
        if cur not in seen:
            seen.add(cur)
            stack.extend(problem.task(cur).predecessors)
    return seen


# ---------------------------------------------------------------------------
# CP-SAT (optional, requires ortools)
# ---------------------------------------------------------------------------

def cpsat_available() -> bool:
    try:
        import ortools  # noqa: F401
        return True
    except Exception:
        return False


def solve_cpsat(problem: Problem, time_limit: float = 30.0) -> Solution:
    if not cpsat_available():
        return Solution(
            method="cpsat",
            stations=[],
            status="unavailable",
            note="ortools is not installed (pip install balancelab[optimize])",
        )
    from ortools.sat.python import cp_model

    problem.check_task_times()
    takt = problem.require_takt()
    greedy = solve_greedy(problem)
    ub = greedy.n_stations
    scale = 10000
    times = {t.id: int(round(t.time * scale)) for t in problem.tasks}
    takt_i = int(round(takt * scale))

    model = cp_model.CpModel()
    ids = problem.ids
    x = {}
    for tid in ids:
        for s in range(ub):
            x[(tid, s)] = model.NewBoolVar("x_%s_%d" % (tid, s))
    y = [model.NewBoolVar("y_%d" % s) for s in range(ub)]
    station_of = {}
    for tid in ids:
        model.Add(sum(x[(tid, s)] for s in range(ub)) == 1)
        station_of[tid] = sum(s * x[(tid, s)] for s in range(ub))
    for s in range(ub):
        model.Add(
            sum(times[tid] * x[(tid, s)] for tid in ids) <= takt_i
        )
        for tid in ids:
            model.Add(x[(tid, s)] <= y[s])
    for s in range(ub - 1):
        model.Add(y[s] >= y[s + 1])  # fill stations in order (symmetry break)
    for t in problem.tasks:
        for p in t.predecessors:
            model.Add(station_of[t.id] >= station_of[p])
    model.Minimize(sum(y))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return Solution(
            method="cpsat",
            stations=[],
            status="infeasible",
            note="CP-SAT found no solution (status %s)" % status,
        )
    assign = {
        tid: next(s for s in range(ub) if solver.Value(x[(tid, s)]))
        for tid in ids
    }
    stations = _stations_from_assignment(problem, assign)
    bad = verify(problem, stations)
    if bad:  # pragma: no cover - numeric scaling guard
        return Solution(
            method="cpsat",
            stations=[],
            status="infeasible",
            note="CP-SAT result failed verification: %s" % bad,
        )
    sol = Solution(
        method="cpsat",
        stations=stations,
        note="optimal" if status == cp_model.OPTIMAL else "feasible (time limit)",
    )
    return evaluate(problem, sol)
