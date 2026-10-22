import pytest

from balancelab.model import (
    InfeasibleError,
    Problem,
    ProblemError,
    Task,
    compute_takt,
    load_csv,
    load_json,
    problem_from_rows,
)


def test_compute_takt():
    assert compute_takt(27000, 450) == 60.0
    assert compute_takt(480, 8) == 60.0


def test_compute_takt_rejects_nonpositive():
    with pytest.raises(ProblemError):
        compute_takt(0, 10)
    with pytest.raises(ProblemError):
        compute_takt(100, 0)


def test_duplicate_id_rejected():
    with pytest.raises(ProblemError):
        Problem([Task("A", "a", 5), Task("A", "b", 6)], takt=10)


def test_unknown_predecessor_rejected():
    with pytest.raises(ProblemError):
        Problem([Task("A", "a", 5, ("ZZ",))], takt=10)


def test_cycle_rejected():
    with pytest.raises(ProblemError):
        Problem(
            [Task("A", "a", 5, ("B",)), Task("B", "b", 5, ("A",))], takt=10
        )


def test_negative_time_rejected():
    with pytest.raises(ProblemError):
        Problem([Task("A", "a", -1)], takt=10)


def test_lower_bound_stations():
    p = problem_from_rows(
        [{"id": "A", "time": 50}, {"id": "B", "time": 45}], takt=60
    )
    assert p.total_time == 95
    assert p.lower_bound_stations() == 2


def test_task_longer_than_takt_is_infeasible():
    p = problem_from_rows([{"id": "A", "time": 70}], takt=60)
    with pytest.raises(InfeasibleError):
        p.check_task_times()


def test_load_csv(tmp_path):
    path = tmp_path / "tasks.csv"
    path.write_text(
        "id,name,time,predecessors\nA,first,10,\nB,second,20,A\n",
        encoding="utf-8",
    )
    p = load_csv(str(path), takt=30)
    assert p.ids == ["A", "B"]
    assert p.task("B").predecessors == ("A",)
    assert p.total_time == 30


def test_load_json_with_embedded_takt(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        '{"takt": 25, "tasks": [{"id": "A", "time": 10},'
        ' {"id": "B", "time": 20, "predecessors": ["A"]}]}',
        encoding="utf-8",
    )
    p = load_json(str(path))
    assert p.takt == 25
    assert p.task("B").predecessors == ("A",)


def test_descendants_and_successors():
    p = problem_from_rows(
        [
            {"id": "A", "time": 5},
            {"id": "B", "time": 5, "predecessors": "A"},
            {"id": "C", "time": 5, "predecessors": "B"},
            {"id": "D", "time": 5, "predecessors": "A"},
        ],
        takt=60,
    )
    assert p.descendants("A") == {"B", "C", "D"}
    assert p.successors()["A"] == ["B", "D"]
