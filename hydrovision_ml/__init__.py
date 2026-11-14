"""hydrovision_ml - Physics-informed neural surrogate package for urban flood forecasting.

Exports public API functions defined in CONTRACT.md.
"""

from hydrovision_ml.api import (
    compute_metrics,
    forecast,
    forecast_batch,
    get_config,
    get_model_info,
    get_terrain,
    load_all,
    run_solver,
)

__version__ = "1.0.0"
__all__ = [
    "load_all",
    "get_config",
    "get_terrain",
    "forecast",
    "forecast_batch",
    "run_solver",
    "compute_metrics",
    "get_model_info",
]

