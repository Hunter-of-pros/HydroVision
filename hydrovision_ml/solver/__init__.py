"""Hydrodynamic Shallow Water Equation solver and scenario generation subpackage.

Phase: Phase 2 (Numerical Hydrodynamic Solver)
"""

from hydrovision_ml.solver.scenarios import make_rain_series, sample_scenarios
from hydrovision_ml.solver.swe_solver import run_solver_core

__all__ = [
    "run_solver_core",
    "make_rain_series",
    "sample_scenarios",
]
