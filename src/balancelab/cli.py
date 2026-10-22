"""Command line interface.

Usage:
    balancelab solve tasks.csv --takt 60 --out report.md
    balancelab solve tasks.csv --available-time 27000 --demand 450 --out r.md
    balancelab --demo
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .demo import demo_problem
from .metrics import Solution
from .model import InfeasibleError, Problem, ProblemError, compute_takt, load_problem
from .report import results_to_json, results_to_markdown, write_load_chart
from .solvers import solve_cpsat, solve_greedy, solve_local


def run_solvers(problem: Problem, methods: List[str]) -> List[Solution]:
    solutions: List[Solution] = []
    greedy = None
    for name in methods:
        if name == "greedy":
            greedy = solve_greedy(problem)
            solutions.append(greedy)
        elif name == "local":
            if greedy is None:
                greedy = solve_greedy(problem)
            solutions.append(solve_local(problem, start=greedy))
        elif name == "cpsat":
            solutions.append(solve_cpsat(problem))
        else:  # pragma: no cover - argparse choices guard this
            raise ProblemError("unknown method: %s" % name)
    return solutions


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="balancelab",
        description="Assembly line balancing and bottleneck optimization",
    )
    parser.add_argument(
        "--demo", action="store_true", help="run the built-in 15-task demo"
    )
    sub = parser.add_subparsers(dest="command")
    sp = sub.add_parser("solve", help="solve a task file (CSV or JSON)")
    sp.add_argument("file", help="task list file (.csv or .json)")
    sp.add_argument("--takt", type=float, default=None, help="takt / cycle time")
    sp.add_argument(
        "--available-time", type=float, default=None,
        help="available production time (with --demand)",
    )
    sp.add_argument("--demand", type=float, default=None, help="demand quantity")
    sp.add_argument(
        "--methods", default="greedy,local,cpsat",
        help="comma-separated subset of greedy,local,cpsat",
    )
    sp.add_argument("--out", default=None, help="write Markdown report here")
    sp.add_argument("--json-out", default=None, help="write JSON report here")
    sp.add_argument(
        "--chart", default=None,
        help="write a Plotly HTML load chart for the best solution (needs plotly)",
    )
    return parser.parse_args(argv)


def _emit(problem, solutions, args) -> int:
    md = results_to_markdown(problem, solutions)
    if getattr(args, "out", None):
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print("Markdown report written to %s" % args.out)
    else:
        print(md)
    if getattr(args, "json_out", None):
        with open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(results_to_json(problem, solutions))
        print("JSON report written to %s" % args.json_out)
    if getattr(args, "chart", None):
        feasible = [s for s in solutions if s.status == "feasible"]
        if not feasible:
            print("no feasible solution to chart", file=sys.stderr)
            return 1
        best = min(feasible, key=lambda s: (s.n_stations, s.smoothness_index))
        write_load_chart(best, args.chart)
        print("Load chart written to %s" % args.chart)
    return 0


def main(argv=None) -> int:
    args = _parse_args(argv)
    try:
        if args.demo:
            problem = demo_problem()
            solutions = run_solvers(problem, ["greedy", "local", "cpsat"])
            return _emit(problem, solutions, args)
        if args.command == "solve":
            takt = args.takt
            if takt is None and args.available_time is not None and args.demand:
                takt = compute_takt(args.available_time, args.demand)
            problem = load_problem(args.file, takt=takt)
            if problem.takt is None:
                print(
                    "error: takt not given (use --takt or --available-time "
                    "+ --demand, or embed \"takt\" in a JSON file)",
                    file=sys.stderr,
                )
                return 2
            methods = [m.strip() for m in args.methods.split(",") if m.strip()]
            solutions = run_solvers(problem, methods)
            return _emit(problem, solutions, args)
        print("nothing to do: use `balancelab solve <file>` or `--demo`",
              file=sys.stderr)
        return 2
    except InfeasibleError as exc:
        print("infeasible: %s" % exc, file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    except ProblemError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
