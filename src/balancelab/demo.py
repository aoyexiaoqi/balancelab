"""Built-in demo dataset: a synthetic 15-task assembly problem.

Identical to ``examples/tasks15.csv`` in the repository (a test keeps the
two in sync).  The data is synthetic example data, not a real production
line.  With takt 60 the total work content is 495, so the theoretical
minimum is 9 stations.
"""
from __future__ import annotations

from .model import Problem, problem_from_rows

DEMO_TAKT = 60.0

DEMO_ROWS = [
    {"id": "T01", "name": "Base frame prep", "time": 42, "predecessors": ""},
    {"id": "T02", "name": "Motor mount", "time": 24, "predecessors": ""},
    {"id": "T03", "name": "Gearbox fit", "time": 36, "predecessors": "T01"},
    {"id": "T04", "name": "Shaft assembly", "time": 28, "predecessors": "T01,T02"},
    {"id": "T05", "name": "Motor install", "time": 48, "predecessors": "T02"},
    {"id": "T06", "name": "Coupling align", "time": 20, "predecessors": "T03"},
    {"id": "T07", "name": "Wiring harness", "time": 33, "predecessors": "T05"},
    {"id": "T08", "name": "Sensor fit", "time": 29, "predecessors": "T06"},
    {"id": "T09", "name": "Control box", "time": 45, "predecessors": "T06,T07"},
    {"id": "T10", "name": "Cover fit", "time": 21, "predecessors": "T08"},
    {"id": "T11", "name": "Calibration", "time": 38, "predecessors": "T09"},
    {"id": "T12", "name": "Label & pack prep", "time": 26, "predecessors": "T09"},
    {"id": "T13", "name": "Functional test", "time": 33, "predecessors": "T10,T11"},
    {"id": "T14", "name": "Final inspection", "time": 28, "predecessors": "T12"},
    {"id": "T15", "name": "Packing", "time": 44, "predecessors": "T13,T14"},
]


def demo_problem() -> Problem:
    return problem_from_rows(DEMO_ROWS, takt=DEMO_TAKT)
