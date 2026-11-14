"""Evaluation plot generators for reporting, documentation, and hackathon presentation.

Phase: Phase 6 (Evaluation Suite)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import numpy as np


def plot_depth_comparison(
    pred_frame: np.ndarray,
    target_frame: np.ndarray,
    terrain: Optional[np.ndarray] = None,
    out_path: Optional[str] = "artifacts/reports/comparison.png",
) -> None:
    """Generate side-by-side heatmaps of predicted vs solver flood depths and error difference map.

    Parameters
    ----------
    pred_frame : np.ndarray
        2D grid of predicted depth (rows, cols) [m].
    target_frame : np.ndarray
        2D grid of ground-truth solver depth (rows, cols) [m].
    terrain : Optional[np.ndarray]
        Optional DEM background for contour overlay.
    out_path : Optional[str]
        File path to save the generated figure.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Depth comparison plot generation.")


def plot_timeseries_at_points(
    pred_frames: np.ndarray,
    target_frames: np.ndarray,
    points: List[Tuple[int, int]],
    dt_s: float = 60.0,
    out_path: Optional[str] = "artifacts/reports/timeseries.png",
) -> None:
    """Plot water depth hydrograph curves over time at selected probe points (e.g. low-lying basins).

    Parameters
    ----------
    pred_frames : np.ndarray
        Predicted sequence of shape (T, rows, cols).
    target_frames : np.ndarray
        Ground-truth sequence of shape (T, rows, cols).
    points : list[tuple[int, int]]
        List of (row, col) grid coordinates to probe.
    dt_s : float
        Time step interval in seconds.
    out_path : Optional[str]
        File path to save the generated figure.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Time series hydrograph plot generation.")


def plot_error_distribution(
    pred_frames: np.ndarray,
    target_frames: np.ndarray,
    out_path: Optional[str] = "artifacts/reports/error_dist.png",
) -> None:
    """Plot histogram and CDF of point-wise prediction errors across the simulation horizon.

    Parameters
    ----------
    pred_frames : np.ndarray
        Predicted sequence.
    target_frames : np.ndarray
        Ground-truth sequence.
    out_path : Optional[str]
        File path to save the generated figure.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Error distribution plot generation.")

