"""Problem model: tasks, precedence, loaders (CSV / JSON), takt time.

A *problem* is a set of tasks with standard times and precedence relations
(the classic SALBP-1 setting: assign tasks to stations so that no station
load exceeds the takt / cycle time and precedence is respected).
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set


class ProblemError(ValueError):
    """Raised for malformed problem data."""


class InfeasibleError(RuntimeError):
    """Raised when no feasible assignment can exist for the given takt."""


@dataclass(frozen=True)
class Task:
    id: str
    name: str
    time: float
    predecessors: tuple = ()


@dataclass
class Problem:
    tasks: List[Task]
    takt: Optional[float] = None

    def __post_init__(self) -> None:
        self._by_id: Dict[str, Task] = {}
        for t in self.tasks:
            if t.id in self._by_id:
                raise ProblemError("duplicate task id: %s" % t.id)
            if t.time < 0:
                raise ProblemError("task %s has negative time" % t.id)
            self._by_id[t.id] = t
        for t in self.tasks:
            for p in t.predecessors:
                if p not in self._by_id:
                    raise ProblemError(
                        "task %s lists unknown predecessor %s" % (t.id, p)
                    )
                if p == t.id:
                    raise ProblemError("task %s is its own predecessor" % t.id)
        self._check_acyclic()

    # -- basic accessors -------------------------------------------------
    def task(self, task_id: str) -> Task:
        return self._by_id[task_id]

    @property
    def ids(self) -> List[str]:
        return [t.id for t in self.tasks]

    @property
    def total_time(self) -> float:
        return float(sum(t.time for t in self.tasks))

    def successors(self) -> Dict[str, List[str]]:
        succ: Dict[str, List[str]] = {t.id: [] for t in self.tasks}
        for t in self.tasks:
            for p in t.predecessors:
                succ[p].append(t.id)
        return succ

    def descendants(self, task_id: str) -> Set[str]:
        succ = self.successors()
        seen: Set[str] = set()
        stack = list(succ[task_id])
        while stack:
            cur = stack.pop()
            if cur not in seen:
                seen.add(cur)
                stack.extend(succ[cur])
        return seen

    # -- takt ------------------------------------------------------------
    def require_takt(self) -> float:
        if self.takt is None:
            raise ProblemError("takt time is not set")
        if self.takt <= 0:
            raise ProblemError("takt time must be positive")
        return float(self.takt)

    def lower_bound_stations(self) -> int:
        """Theoretical minimum station count: ceil(total_time / takt)."""
        takt = self.require_takt()
        return int(math.ceil(self.total_time / takt - 1e-9))

    def check_task_times(self) -> None:
        """A single task longer than the takt makes the problem infeasible."""
        takt = self.require_takt()
        for t in self.tasks:
            if t.time > takt + 1e-9:
                raise InfeasibleError(
                    "task %s (time %s) exceeds takt %s; no feasible assignment"
                    % (t.id, t.time, takt)
                )

    # -- validation ------------------------------------------------------
    def _check_acyclic(self) -> None:
        # Kahn's algorithm
        succ = self.successors()
        indeg = {t.id: len(t.predecessors) for t in self.tasks}
        queue = [tid for tid, d in indeg.items() if d == 0]
        visited = 0
        while queue:
            cur = queue.pop()
            visited += 1
            for nxt in succ[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if visited != len(self.tasks):
            raise ProblemError("precedence graph contains a cycle")


def compute_takt(available_time: float, demand: float) -> float:
    """Takt time = available production time / customer demand."""
    if available_time <= 0:
        raise ProblemError("available time must be positive")
    if demand <= 0:
        raise ProblemError("demand must be positive")
    return float(available_time) / float(demand)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _parse_predecessors(raw) -> tuple:
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple)):
        return tuple(str(x).strip() for x in raw if str(x).strip())
    text = str(raw).strip()
    if not text:
        return ()
    parts = text.replace(";", ",").split(",")
    return tuple(p.strip() for p in parts if p.strip())


def problem_from_rows(rows: Sequence[dict], takt: Optional[float] = None) -> Problem:
    tasks = []
    for row in rows:
        tid = str(row.get("id", "")).strip()
        if not tid:
            raise ProblemError("every task row needs an id")
        name = str(row.get("name", tid)).strip() or tid
        try:
            tval = float(row.get("time"))
        except (TypeError, ValueError):
            raise ProblemError("task %s has a non-numeric time" % tid)
        tasks.append(
            Task(
                id=tid,
                name=name,
                time=tval,
                predecessors=_parse_predecessors(row.get("predecessors", "")),
            )
        )
    if not tasks:
        raise ProblemError("no tasks found")
    return Problem(tasks=tasks, takt=takt)


def load_csv(path: str, takt: Optional[float] = None) -> Problem:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ProblemError("empty CSV file")
        rows = list(reader)
    return problem_from_rows(rows, takt=takt)


def load_json(path: str, takt: Optional[float] = None) -> Problem:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        rows = data.get("tasks", [])
        if takt is None and data.get("takt") is not None:
            takt = float(data["takt"])
    else:
        rows = data
    return problem_from_rows(list(rows), takt=takt)


def load_problem(path: str, takt: Optional[float] = None) -> Problem:
    if path.lower().endswith(".json"):
        return load_json(path, takt=takt)
    return load_csv(path, takt=takt)
