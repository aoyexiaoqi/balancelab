import os

from balancelab.demo import DEMO_ROWS, demo_problem
from balancelab.metrics import verify
from balancelab.model import load_csv, load_json
from balancelab.solvers import solve_greedy, solve_local

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "examples", "tasks15.csv")
JSON = os.path.join(HERE, "..", "examples", "tasks15.json")


def test_examples_csv_and_json_agree():
    a = load_csv(CSV, takt=60)
    b = load_json(JSON)
    assert a.ids == b.ids
    assert a.total_time == b.total_time == 495.0
    for t in a.tasks:
        other = b.task(t.id)
        assert (t.time, t.predecessors) == (other.time, other.predecessors)


def test_demo_problem_matches_example_files():
    p = demo_problem()
    a = load_csv(CSV, takt=60)
    assert p.ids == a.ids
    assert p.total_time == a.total_time
    assert len(DEMO_ROWS) == 15
    assert p.lower_bound_stations() == 9


def test_examples_regression_station_counts():
    # Regression case: on the synthetic 15-task example both heuristics
    # reach 10 stations (lower bound 9); verified against CP-SAT optimum.
    p = load_csv(CSV, takt=60)
    greedy = solve_greedy(p)
    local = solve_local(p, start=greedy)
    for sol in (greedy, local):
        assert verify(p, sol.stations) == []
        assert sol.n_stations == 10
        assert sol.efficiency == 495.0 / 600.0
