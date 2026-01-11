"""
Single Problem Engine Package

Re-exports all public API for backwards compatibility.
"""

from .engine import SingleProblemEngine
from .functions import (
    run_single_problem,
    run_single_problem_from_phase,
    compute_thresholds
)

__all__ = [
    "SingleProblemEngine",
    "run_single_problem",
    "run_single_problem_from_phase",
    "compute_thresholds",
]
