import json
import os

from balancelab.cli import main

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "examples", "tasks15.csv")


def test_demo_runs(capsys):
    assert main(["--demo"]) == 0
    out = capsys.readouterr().out
    assert "greedy-rpw" in out
    assert "82.5%" in out


def test_solve_writes_markdown_and_json(tmp_path):
    md = tmp_path / "report.md"
    js = tmp_path / "report.json"
    rc = main(
        [
            "solve", CSV,
            "--takt", "60",
            "--methods", "greedy,local",
            "--out", str(md),
            "--json-out", str(js),
        ]
    )
    assert rc == 0
    assert "Method comparison" in md.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["problem"]["n_tasks"] == 15
    assert data["problem"]["lower_bound_stations"] == 9
    methods = {s["method"]: s for s in data["solutions"]}
    assert methods["greedy-rpw"]["n_stations"] == 10
    assert methods["greedy-rpw"]["efficiency"] == 495.0 / 600.0


def test_solve_takt_from_available_time_and_demand(tmp_path):
    md = tmp_path / "r.md"
    rc = main(
        [
            "solve", CSV,
            "--available-time", "27000",
            "--demand", "450",
            "--methods", "greedy",
            "--out", str(md),
        ]
    )
    assert rc == 0
    assert "Takt: 60" in md.read_text(encoding="utf-8")


def test_solve_without_takt_fails(tmp_path):
    plain = tmp_path / "plain.csv"
    plain.write_text("id,time\nA,10\n", encoding="utf-8")
    assert main(["solve", str(plain)]) == 2


def test_solve_infeasible_returns_1(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,time\nA,70\n", encoding="utf-8")
    assert main(["solve", str(bad), "--takt", "60"]) == 1
