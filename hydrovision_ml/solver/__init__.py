"""Hydrodynamic numerical solver subpackage.

Contains 2D shallow water equation (SWE) solver core and rainfall scenario generators.
"""

from hydrovision_ml.solver.scenarios import make_rain_series, sample_scenarios
from hydrovision_ml.solver.swe_solver import run_solver_core

__all__ = ["run_solver_core", "make_rain_series", "sample_scenarios"]

