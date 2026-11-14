"""Autoregressive multi-step rollout module for surrogate inference.

Phase: Phase 4 & 5
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any, List

import numpy as np


def rollout(
    model: Any,
    initial_depth: np.ndarray,
    terrain: np.ndarray,
    rain_series: List[float],
    drain_capacity_mmhr: float = 0.0,
    horizon_steps: int = 120,
    device: str = "cpu",
) -> np.ndarray:
    """Execute autoregressive rollout of the neural surrogate over the full temporal horizon.

    Parameters
    ----------
    model : Any
        Loaded neural surrogate model (e.g. UNetSurrogate).
    initial_depth : np.ndarray
        Initial depth grid of shape (rows, cols) at t=0 (usually all zeros).
    terrain : np.ndarray
        Static elevation DEM grid of shape (rows, cols).
    rain_series : list[float]
        Rainfall intensity for each time step [mm/hr].
    drain_capacity_mmhr : float
        Uniform drain capacity sink [mm/hr].
    horizon_steps : int
        Number of steps to advance (default: 120).
    device : str
        Inference compute device ("cpu", "cuda", "mps").

    Returns
    -------
    np.ndarray
        Predicted depth sequence of shape (horizon_steps + 1, rows, cols) in meters.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 4.
    """
    raise NotImplementedError("Planned for Phase 4: Autoregressive multi-step neural rollout.")

