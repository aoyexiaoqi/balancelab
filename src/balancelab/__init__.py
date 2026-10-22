"""BalanceLab — assembly line balancing and bottleneck optimization."""
from .metrics import Solution, evaluate, verify
from .model import (
    InfeasibleError,
    Problem,
    ProblemError,
    Task,
    compute_takt,
    load_problem,
)
from .solvers import cpsat_available, solve_cpsat, solve_greedy, solve_local

__version__ = "0.1.0"

__all__ = [
    "Problem",
    "Task",
    "ProblemError",
    "InfeasibleError",
    "Solution",
    "compute_takt",
    "load_problem",
    "evaluate",
    "verify",
    "solve_greedy",
    "solve_local",
    "solve_cpsat",
    "cpsat_available",
    "__version__",
]
