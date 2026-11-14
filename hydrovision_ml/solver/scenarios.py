"""Rainfall hyetograph and scenario generation utilities.

Phase: Phase 2 (Numerical Solver & Scenarios)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np

from hydrovision_ml.config import DT_S, HORIZON_STEPS


def make_rain_series(
    duration_min: float,
    intensity_mmhr: float,
    shape: str = "constant",
    dt_s: float = float(DT_S),
    total_steps: int = HORIZON_STEPS,
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
    """
    duration_steps = min(total_steps, max(1, int(round((duration_min * 60.0) / dt_s))))
    series = np.zeros(total_steps, dtype=np.float64)

    if shape == "triangular":
        half = max(1, duration_steps // 2)
        for i in range(duration_steps):
            if i <= half:
                series[i] = intensity_mmhr * (i / half)
            else:
                series[i] = intensity_mmhr * max(0.0, 1.0 - (i - half) / (duration_steps - half))
    elif shape == "double_peak":
        p1 = max(1, duration_steps // 3)
        p2 = max(1, 2 * duration_steps // 3)
        w_width = max(1.0, duration_steps / 8.0)
        for i in range(duration_steps):
            w1 = np.exp(-((i - p1) ** 2) / (2.0 * (w_width ** 2)))
            w2 = np.exp(-((i - p2) ** 2) / (2.0 * (w_width ** 2)))
            series[i] = intensity_mmhr * min(1.0, float(w1 + 0.85 * w2))
    else:  # "constant" or default
        series[:duration_steps] = intensity_mmhr

    return [round(float(v), 2) for v in series]


def sample_scenarios(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """Sample diverse rainfall scenarios across parameter space using Latin Hypercube / Stratified Sampling.

    Parameters
    ----------
    n : int
        Number of distinct scenarios to generate.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    list[dict]
        List of parameter dictionaries suitable for training set generation:
        - rain_intensity_mmhr: float [20.0, 150.0]
        - rain_duration_min: float [15.0, 90.0]
        - rain_shape: str ("constant" | "triangular" | "double_peak")
        - drain_capacity_mmhr: float [0.0, 30.0]
        - horizon_steps: int (120)
    """
    rng = np.random.default_rng(seed)
    shapes = ["constant", "triangular", "double_peak"]
    scenarios = []

    # Stratified bins for even coverage
    for i in range(n):
        # Intensity stratified between 20 and 150 mm/hr
        bin_i = (i + rng.uniform(0.05, 0.95)) / n
        intensity = 20.0 + bin_i * (150.0 - 20.0)

        # Duration stratified between 15 and 90 min
        bin_d = ((i * 7) % n + rng.uniform(0.05, 0.95)) / n
        duration = 15.0 + bin_d * (90.0 - 15.0)

        # Drainage stratified between 0 and 30 mm/hr
        bin_drain = ((i * 13) % n + rng.uniform(0.05, 0.95)) / n
        drain = 0.0 + bin_drain * (30.0 - 0.0)

        shape = shapes[i % len(shapes)]

        scenarios.append(
            {
                "rain_intensity_mmhr": round(float(intensity), 1),
                "rain_duration_min": round(float(duration), 1),
                "rain_shape": shape,
                "drain_capacity_mmhr": round(float(drain), 1),
                "horizon_steps": int(HORIZON_STEPS),
            }
        )

    return scenarios
