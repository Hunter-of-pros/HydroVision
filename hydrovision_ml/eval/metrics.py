"""Formal hydrological evaluation metrics defined in CONTRACT.md Section 5.

Quantifies spatial accuracy, peak flood depth, inundated extent (IoU),
mass conservation fidelity, and wetting front arrival timing.

Phase: Phase 6 (Evaluation Suite)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any


def mean_absolute_error(pred: Any, target: Any) -> float:
    """Compute Mean Absolute Error (MAE) in meters across all grid cells and time frames.

    Formula: MAE = (1 / (T * H * W)) * sum(|h_pred - h_true|)

    Parameters
    ----------
    pred : array-like
        Predicted depth array of shape (T, H, W).
    target : array-like
        Ground-truth depth array of matching shape.

    Returns
    -------
    float
        MAE in meters.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Evaluation metrics (MAE).")


def root_mean_square_error(pred: Any, target: Any) -> float:
    """Compute Root Mean Square Error (RMSE) in meters across all grid cells and time frames.

    Formula: RMSE = sqrt((1 / (T * H * W)) * sum((h_pred - h_true)^2))

    Parameters
    ----------
    pred : array-like
        Predicted depth array of shape (T, H, W).
    target : array-like
        Ground-truth depth array of matching shape.

    Returns
    -------
    float
        RMSE in meters.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Evaluation metrics (RMSE).")


def peak_depth_error(pred: Any, target: Any) -> float:
    """Compute absolute discrepancy in peak water depth over the full event.

    Formula: Peak Error = |max(h_pred) - max(h_true)|

    Parameters
    ----------
    pred : array-like
        Predicted depth array.
    target : array-like
        Ground-truth depth array.

    Returns
    -------
    float
        Peak depth error in meters.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Evaluation metrics (Peak Depth Error).")


def wet_iou(pred: Any, target: Any, threshold: float = 0.05) -> float:
    """Compute Intersection over Union (IoU / Critical Success Index) for wet cells.

    A cell is considered inundated (wet) if water depth >= threshold (default: 0.05 m = 5 cm).
    Computed over the maximum flood footprint or final frame.

    Formula: IoU = |Wet_pred ∩ Wet_true| / |Wet_pred ∪ Wet_true|

    Parameters
    ----------
    pred : array-like
        Predicted depth array.
    target : array-like
        Ground-truth depth array.
    threshold : float
        Inundation cutoff threshold in meters (default: 0.05 m).

    Returns
    -------
    float
        IoU score in range [0.0, 1.0].

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Evaluation metrics (Wet IoU).")


def mass_balance_relative_error(pred: Any, target: Any) -> float:
    """Compute relative global water volume discrepancy at the final time horizon.

    Formula: Mass Error = |Volume_pred - Volume_true| / max(Volume_true, 1e-6)

    Parameters
    ----------
    pred : array-like
        Predicted depth array.
    target : array-like
        Ground-truth depth array.

    Returns
    -------
    float
        Fractional mass conservation error.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Evaluation metrics (Mass Error).")


def arrival_time_error(
    pred: Any,
    target: Any,
    threshold: float = 0.05,
    dt_s: float = 60.0,
) -> float:
    """Compute difference in wetting front arrival time at vulnerable low-lying cells.

    Arrival time is defined as the earliest time step where water depth exceeds threshold.

    Formula: Arrival Error = |t_arr_pred - t_arr_true| [seconds]

    Parameters
    ----------
    pred : array-like
        Predicted depth sequence of shape (T, H, W).
    target : array-like
        Ground-truth depth sequence of shape (T, H, W).
    threshold : float
        Inundation cutoff threshold in meters (default: 0.05 m).
    dt_s : float
        Temporal interval per step in seconds (default: 60.0).

    Returns
    -------
    float
        Arrival time discrepancy in seconds.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 6.
    """
    raise NotImplementedError("Planned for Phase 6: Evaluation metrics (Arrival Time Error).")

