import math

from balancelab.metrics import Solution, evaluate, verify
from balancelab.model import problem_from_rows


def _problem():
    return problem_from_rows(
        [
            {"id": "A", "time": 30},
            {"id": "B", "time": 20, "predecessors": "A"},
            {"id": "C", "time": 30},
        ],
        takt=60,
    )


def test_evaluate_hand_computed():
    p = _problem()
    sol = evaluate(p, Solution(method="manual", stations=[["A", "B"], ["C"]]))
    assert sol.loads == [50.0, 30.0]
    assert sol.total_time == 80.0
    # efficiency = 80 / (2 * 60)
    assert sol.efficiency == 80.0 / 120.0
    assert sol.balance_delay == 1.0 - 80.0 / 120.0
    # smoothness = sqrt((50-50)^2 + (50-30)^2) = 20
    assert sol.smoothness_index == 20.0
    assert sol.bottleneck_station == 0
    assert sol.bottleneck_load == 50.0
    assert sol.idle_times == [10.0, 30.0]
    assert sol.total_idle == 40.0


def test_evaluate_perfect_balance():
    p = problem_from_rows(
        [{"id": "A", "time": 30}, {"id": "B", "time": 30}], takt=30
    )
    sol = evaluate(p, Solution(method="manual", stations=[["A"], ["B"]]))
    assert sol.efficiency == 1.0
    assert sol.smoothness_index == 0.0


def test_verify_accepts_feasible():
    p = _problem()
    assert verify(p, [["A", "B"], ["C"]]) == []


def test_verify_catches_precedence_violation():
    p = _problem()
    bad = verify(p, [["B"], ["A"], ["C"]])  # B before its predecessor A
    assert any("precedence" in msg for msg in bad)


def test_verify_catches_overload():
    p = problem_from_rows(
        [{"id": "A", "time": 40}, {"id": "B", "time": 40}], takt=60
    )
    bad = verify(p, [["A", "B"]])
    assert any("exceeds takt" in msg for msg in bad)


def test_verify_catches_missing_and_duplicate():
    p = _problem()
    bad = verify(p, [["A", "A"], ["C"]])
    assert any("more than once" in msg for msg in bad)
    assert any("not assigned" in msg for msg in bad)


def test_smoothness_uses_max_load():
    p = problem_from_rows(
        [{"id": "A", "time": 10}, {"id": "B", "time": 9}, {"id": "C", "time": 8}],
        takt=12,
    )
    sol = evaluate(p, Solution(method="m", stations=[["A"], ["B"], ["C"]]))
    assert sol.smoothness_index == math.sqrt(0 + 1 + 4)
