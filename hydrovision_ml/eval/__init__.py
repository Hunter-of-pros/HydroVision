"""Evaluation subpackage for HydroVision.

Phase: Phase 6 (Evaluation Suite & Benchmarks)
"""

from hydrovision_ml.eval.metrics import (
    arrival_time_error,
    compute_all_metrics,
    mass_balance_relative_error,
    mean_absolute_error,
    peak_depth_error,
    root_mean_square_error,
    wet_iou,
)

__all__ = [
    "mean_absolute_error",
    "root_mean_square_error",
    "peak_depth_error",
    "wet_iou",
    "mass_balance_relative_error",
    "arrival_time_error",
    "compute_all_metrics",
]
