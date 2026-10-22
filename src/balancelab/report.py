"""Markdown / JSON reporting and an optional Plotly load chart."""
from __future__ import annotations

import json
from typing import List, Optional

from .metrics import Solution
from .model import Problem


def solution_to_dict(problem: Problem, sol: Solution) -> dict:
    data = {
        "method": sol.method,
        "status": sol.status,
        "note": sol.note,
        "n_stations": sol.n_stations,
        "stations": [
            {
                "station": i + 1,
                "tasks": list(station),
                "load": (sol.loads[i] if i < len(sol.loads) else None),
                "idle": (sol.idle_times[i] if i < len(sol.idle_times) else None),
            }
            for i, station in enumerate(sol.stations)
        ],
    }
    if sol.status == "feasible":
        data.update(
            {
                "efficiency": sol.efficiency,
                "balance_delay": sol.balance_delay,
                "smoothness_index": sol.smoothness_index,
                "bottleneck_station": sol.bottleneck_station + 1,
                "bottleneck_load": sol.bottleneck_load,
                "total_idle": sol.total_idle,
            }
        )
    return data


def results_to_dict(problem: Problem, solutions: List[Solution]) -> dict:
    return {
        "problem": {
            "n_tasks": len(problem.tasks),
            "total_time": problem.total_time,
            "takt": problem.takt,
            "lower_bound_stations": (
                problem.lower_bound_stations()
                if problem.takt is not None
                else None
            ),
        },
        "solutions": [solution_to_dict(problem, s) for s in solutions],
    }


def results_to_json(problem: Problem, solutions: List[Solution]) -> str:
    return json.dumps(results_to_dict(problem, solutions), indent=2,
                      ensure_ascii=False)


def _fmt(x: Optional[float], nd: int = 2) -> str:
    if x is None:
        return "-"
    return ("%.*f" % (nd, x))


def results_to_markdown(problem: Problem, solutions: List[Solution]) -> str:
    lines = []
    lines.append("# BalanceLab 生产线平衡报告 / Line Balancing Report")
    lines.append("")
    lines.append(
        "- 任务数 / Tasks: %d" % len(problem.tasks)
    )
    lines.append(
        "- 总工时 / Total work content: %s" % _fmt(problem.total_time)
    )
    if problem.takt is not None:
        lines.append("- 节拍 / Takt: %s" % _fmt(problem.takt))
        lines.append(
            "- 理论最少工位数 / Lower bound stations: %d"
            % problem.lower_bound_stations()
        )
    lines.append("")
    lines.append("## 方法对比 / Method comparison")
    lines.append("")
    lines.append(
        "| Method | Status | Stations | Efficiency | Smoothness | "
        "Bottleneck | Idle total |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for sol in solutions:
        if sol.status == "feasible":
            lines.append(
                "| %s | %s | %d | %.1f%% | %s | S%d (%s) | %s |"
                % (
                    sol.method,
                    sol.status,
                    sol.n_stations,
                    sol.efficiency * 100.0,
                    _fmt(sol.smoothness_index),
                    sol.bottleneck_station + 1,
                    _fmt(sol.bottleneck_load),
                    _fmt(sol.total_idle),
                )
            )
        else:
            note = sol.note or sol.status
            lines.append(
                "| %s | %s | - | - | - | - | - |" % (sol.method, note)
            )
    lines.append("")
    for sol in solutions:
        if sol.status != "feasible":
            continue
        lines.append("## %s — 工位明细 / Station detail" % sol.method)
        lines.append("")
        lines.append("| Station | Tasks | Load | Idle |")
        lines.append("|---|---|---|---|")
        for i, station in enumerate(sol.stations):
            lines.append(
                "| S%d | %s | %s | %s |"
                % (
                    i + 1,
                    ", ".join(station),
                    _fmt(sol.loads[i]),
                    _fmt(sol.idle_times[i]),
                )
            )
        lines.append("")
        lines.append(
            "- 平衡率 / Efficiency: %.1f%%；瓶颈工位 / Bottleneck: S%d"
            % (sol.efficiency * 100.0, sol.bottleneck_station + 1)
        )
        lines.append("")
    return "\n".join(lines)


def write_load_chart(sol: Solution, path: str) -> str:
    """Write a Plotly HTML bar chart of station loads (needs plotly)."""
    try:
        import plotly.graph_objects as go
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "plotly is not installed (pip install balancelab[plot])"
        ) from exc
    fig = go.Figure(
        data=[
            go.Bar(
                x=["S%d" % (i + 1) for i in range(sol.n_stations)],
                y=sol.loads,
                text=["%s" % _fmt(v) for v in sol.loads],
                textposition="auto",
            )
        ]
    )
    fig.add_hline(y=sol.takt, line_dash="dash", annotation_text="takt")
    fig.update_layout(
        title="Station loads — %s" % sol.method,
        xaxis_title="Station",
        yaxis_title="Load",
    )
    fig.write_html(path)
    return path
