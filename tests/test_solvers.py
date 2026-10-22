import math

import pytest

from balancelab.demo import demo_problem
from balancelab.metrics import verify
from balancelab.model import InfeasibleError, problem_from_rows
from balancelab.solvers import (
    cpsat_available,
    positional_weights,
    solve_cpsat,
    solve_greedy,
    solve_local,
)

SOLVERS = [solve_greedy, solve_local]


def _rows(specs, takt):
    return problem_from_rows(
        [
            {"id": tid, "time": t, "predecessors": preds}
            for tid, t, preds in specs
        ],
        takt=takt,
    )


@pytest.mark.parametrize("solver", SOLVERS)
def test_hand_case_two_stations_full_efficiency(solver):
    # 10 + 20 + 30, takt 30 -> optimum is 2 stations at 100% efficiency
    p = _rows([("A", 10, ""), ("B", 20, ""), ("C", 30, "")], takt=30)
    sol = solver(p)
    assert verify(p, sol.stations) == []
    assert sol.n_stations == 2
    assert sol.efficiency == 1.0


@pytest.mark.parametrize("solver", SOLVERS)
def test_precedence_may_share_a_station(solver):
    p = _rows([("A", 10, ""), ("B", 10, "A")], takt=30)
    sol = solver(p)
    assert sol.n_stations == 1
    assert verify(p, sol.stations) == []


@pytest.mark.parametrize("solver", SOLVERS)
def test_precedence_chain_needs_three_stations(solver):
    p = _rows([("A", 20, ""), ("B", 20, "A"), ("C", 20, "B")], takt=30)
    sol = solver(p)
    assert sol.n_stations == 3
    assert sol.efficiency == pytest.approx(60.0 / 90.0)
    assert verify(p, sol.stations) == []


@pytest.mark.parametrize("solver", SOLVERS)
def test_infeasible_task_raises(solver):
    p = _rows([("A", 70, "")], takt=60)
    with pytest.raises(InfeasibleError):
        solver(p)


@pytest.mark.parametrize("solver", SOLVERS)
def test_demo_invariants(solver):
    p = demo_problem()
    sol = solver(p)
    assert verify(p, sol.stations) == []
    assert all(load <= 60.0 + 1e-9 for load in sol.loads)
    assert sol.n_stations >= p.lower_bound_stations()


def test_positional_weights_include_successors():
    p = _rows(
        [("A", 10, ""), ("B", 20, "A"), ("C", 5, "B")], takt=100
    )
    w = positional_weights(p)
    assert w["A"] == 35.0
    assert w["B"] == 25.0
    assert w["C"] == 5.0


def test_local_search_improves_smoothness():
    # greedy packs [10], [9, 3], [8] (smoothness sqrt(20));
    # moving the 3 next to the 8 evens the loads out.
    p = _rows(
        [("P", 10, ""), ("Q", 9, ""), ("R", 8, ""), ("S", 3, "")], takt=12
    )
    greedy = solve_greedy(p)
    assert greedy.smoothness_index == pytest.approx(math.sqrt(20))
    local = solve_local(p, start=greedy)
    assert verify(p, local.stations) == []
    assert local.n_stations == greedy.n_stations
    assert local.smoothness_index < greedy.smoothness_index - 0.1


def test_local_search_never_worse_than_greedy_on_demo():
    p = demo_problem()
    greedy = solve_greedy(p)
    local = solve_local(p, start=greedy)
    assert (local.n_stations, local.smoothness_index) <= (
        greedy.n_stations,
        greedy.smoothness_index + 1e-9,
    )


@pytest.mark.skipif(cpsat_available(), reason="ortools installed here")
def test_cpsat_reports_unavailable_without_ortools():
    sol = solve_cpsat(demo_problem())
    assert sol.status == "unavailable"
    assert "ortools" in sol.note


@pytest.mark.skipif(not cpsat_available(), reason="ortools not installed")
def test_cpsat_matches_heuristic_station_count_on_demo():
    p = demo_problem()
    sol = solve_cpsat(p)
    assert sol.status == "feasible"
    assert verify(p, sol.stations) == []
    assert sol.n_stations == 10  # proven optimal for the demo data
