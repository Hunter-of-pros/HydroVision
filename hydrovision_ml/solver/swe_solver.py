"""2D Shallow Water Equations (SWE) local-inertial numerical solver core.

Solves the de Almeida & Bates (2012) simplified hydrodynamic equations on a 2D regular
grid with Manning friction, infiltration/drainage sink terms, and adaptive CFL time-stepping.

Phase: Phase 2 (Numerical Solver)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


def run_solver_core(
    dem: np.ndarray,
    rain_series_mmhr: List[float],
    dt_s: float = 60.0,
    drain_capacity_mmhr: float = 0.0,
    manning_n: float = 0.035,
    substep_cfl: float = 0.7,
) -> Dict[str, Any]:
    """Execute high-fidelity 2D hydrodynamic simulation over DEM.

    Parameters
    ----------
    dem : np.ndarray
        Elevation field of shape (rows, cols) in meters.
    rain_series_mmhr : list[float]
        Rainfall intensity per macro time step (length = horizon_steps).
    dt_s : float
        Output frame interval in seconds (default: 60.0).
    drain_capacity_mmhr : float
        Uniform infiltration and drainage capacity sink term in mm/hr (default: 0.0).
    manning_n : float
        Surface roughness coefficient (default: 0.035 for urban/vegetated).
    substep_cfl : float
        Courant-Friedrichs-Lewy safety condition multiplier for adaptive internal sub-stepping.

    Returns
    -------
    dict
        Solver simulation results:
        - depth_frames : np.ndarray of shape (num_frames, rows, cols)
        - times_s : list[int]
        - max_velocity_frames : np.ndarray
        - solve_time_s : float

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 2.
    """
    raise NotImplementedError(
        "Planned for Phase 2: Local-inertial 2D shallow water equation solver."
    )

