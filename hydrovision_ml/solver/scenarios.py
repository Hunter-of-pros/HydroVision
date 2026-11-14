"""Rainfall hyetograph and scenario generation utilities.

Phase: Phase 2 (Numerical Solver)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any, Dict, List


def make_rain_series(
    duration_min: float,
    intensity_mmhr: float,
    shape: str = "constant",
    dt_s: float = 60.0,
    total_steps: int = 120,
) -> List[float]:
    """Construct a discrete rainfall intensity timeseries for a given storm profile.

    Parameters
    ----------
    duration_min : float
        Total duration of precipitation in minutes.
    intensity_mmhr : float
        Peak or constant rainfall intensity in mm/hr.
    shape : str
        Hyetograph shape: "constant", "triangular", or "double_peak".
    dt_s : float
        Sampling interval in seconds (default: 60.0).
    total_steps : int
        Total simulation horizon steps (default: 120).

    Returns
    -------
    list[float]
        Rainfall intensity values for each discrete time step of length total_steps.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 2.
    """
    raise NotImplementedError("Planned for Phase 2: Rainfall scenario generation.")


def sample_scenarios(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """Sample diverse rainfall scenarios across parameter space using Latin Hypercube Sampling.

    Parameters
    ----------
    n : int
        Number of distinct scenarios to generate.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    list[dict]
        List of parameter dictionaries suitable for training set generation.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 2.
    """
    raise NotImplementedError("Planned for Phase 2: Rainfall scenario generation.")

