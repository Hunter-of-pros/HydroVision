"""Formal hydrological evaluation metrics defined in CONTRACT.md Section 5.

Quantifies spatial accuracy, peak flood depth, inundated extent (IoU),
mass conservation fidelity, and wetting front arrival timing.

Phase: Phase 6 (Evaluation Suite)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from hydrovision_ml.config import DT_S, WET_THRESHOLD_M


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
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    return round(float(np.mean(np.abs(p - t))), 4)


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
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    return round(float(np.sqrt(np.mean((p - t) ** 2))), 4)


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
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    max_p = float(np.max(p)) if p.size > 0 else 0.0
    max_t = float(np.max(t)) if t.size > 0 else 0.0
    return round(float(abs(max_p - max_t)), 4)


def wet_iou(pred: Any, target: Any, threshold: float = float(WET_THRESHOLD_M)) -> float:
    """Compute Intersection over Union (IoU / Critical Success Index) for wet cells.

    A cell is considered inundated (wet) if water depth >= threshold (default: 0.05 m = 5 cm).
    Evaluated over the maximum water depth footprint.

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
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)

    # Footprint: max depth across time horizon for each cell
    if p.ndim == 3:
        max_p = np.max(p, axis=0)
        max_t = np.max(t, axis=0)
    else:
        max_p = p
        max_t = t

    wet_p = max_p >= threshold
    wet_t = max_t >= threshold

    intersection = int(np.sum(wet_p & wet_t))
    union = int(np.sum(wet_p | wet_t))

    if union == 0:
        return 1.0  # Both correctly predicted completely dry
    return round(float(intersection / union), 4)


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
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)

    # Volume at final frame
    final_p = p[-1] if p.ndim == 3 else p
    final_t = t[-1] if t.ndim == 3 else t

    vol_p = float(np.sum(np.maximum(0.0, final_p)))
    vol_t = float(np.sum(np.maximum(0.0, final_t)))

    if vol_t < 1e-6:
        return 0.0 if vol_p < 1e-6 else 1.0
    return round(float(abs(vol_p - vol_t) / vol_t), 4)


def arrival_time_error(
    pred: Any,
    target: Any,
    threshold: float = float(WET_THRESHOLD_M),
    dt_s: float = float(DT_S),
) -> float:
    """Compute difference in wetting front arrival time at vulnerable low-lying cells.

    Arrival time is defined as the earliest time step where water depth exceeds threshold.

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
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)

    if p.ndim != 3 or t.ndim != 3:
        return 0.0

    T, H, W = p.shape
    wet_p = p >= threshold
    wet_t = t >= threshold

    # Find first index where wet_p is True along axis 0
    arr_p = np.where(np.any(wet_p, axis=0), np.argmax(wet_p, axis=0) * dt_s, np.nan)
    arr_t = np.where(np.any(wet_t, axis=0), np.argmax(wet_t, axis=0) * dt_s, np.nan)

    # Evaluate on cells that get flooded in ground truth
    mask = ~np.isnan(arr_t)
    if not np.any(mask):
        return 0.0

    valid_diff = np.abs(np.nan_to_num(arr_p[mask], nan=T * dt_s) - arr_t[mask])
    return round(float(np.mean(valid_diff)), 1)


def compute_all_metrics(
    pred: Any,
    target: Any,
    params: Optional[Dict[str, Any]] = None,
    solver_time_s: float = 1.5,
    inference_time_ms: float = 35.0,
) -> Dict[str, Any]:
    """Compute all evaluation metrics defined in CONTRACT.md Section 5.

    Returns
    -------
    dict
        - mae: float
        - rmse: float
        - peak_depth_error: float
        - wet_iou: float
        - mass_error: float
        - arrival_time_error_s: float
        - speedup: float
    """
    mae = mean_absolute_error(pred, target)
    rmse = root_mean_square_error(pred, target)
    pde = peak_depth_error(pred, target)
    iou = wet_iou(pred, target)
    mass_err = mass_balance_relative_error(pred, target)
    arr_err = arrival_time_error(pred, target)

    speedup = round(float((solver_time_s * 1000.0) / max(0.1, inference_time_ms)), 1)

    return {
        "mae": mae,
        "rmse": rmse,
        "peak_depth_error": pde,
        "wet_iou": iou,
        "mass_error": mass_err,
        "arrival_time_error_s": arr_err,
        "speedup": speedup,
    }
