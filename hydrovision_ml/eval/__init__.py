"""Evaluation, metrics, benchmarking, and visualization subpackage for HydroVision.

Phase: Phase 6 (Evaluation Suite)
Owner: ML Teammate
"""

from hydrovision_ml.eval.benchmark import benchmark_speed
from hydrovision_ml.eval.metrics import (
    arrival_time_error,
    mass_balance_relative_error,
    mean_absolute_error,
    peak_depth_error,
    root_mean_square_error,
    wet_iou,
)
from hydrovision_ml.eval.plots import (
    plot_depth_comparison,
    plot_error_distribution,
    plot_timeseries_at_points,
)

__all__ = [
    "mean_absolute_error",
    "root_mean_square_error",
    "peak_depth_error",
    "wet_iou",
    "mass_balance_relative_error",
    "arrival_time_error",
    "benchmark_speed",
    "plot_depth_comparison",
    "plot_timeseries_at_points",
    "plot_error_distribution",
]

