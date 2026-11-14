"""Public API interface for hydrovision_ml.

This module defines the production contract between the ML pipeline and the backend.
All functions in this file are stubs that raise NotImplementedError until the ML
teammate implements the surrogate model and solver in Phases 4 & 5.

Contract conventions:
- Grid shape: 64 rows x 64 columns
- Orientation: row 0 = North, column 0 = West
- Temporal horizon: 120 steps with dt=60s -> 121 output frames (t=0 to t=7200s)
- Rain series length: 120 steps (one precipitation value per interval)
- Units: Water depth in meters (m), Rainfall intensity in mm/hr, Cell size in meters (40m)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def load_all(model_path: str = "artifacts/models/best.pt") -> None:
    """Load neural surrogate weights, normalization parameters, and static terrain into memory.

    Parameters
    ----------
    model_path : str
        Path to the trained PyTorch surrogate checkpoint (.pt file).

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4 (Surrogate model training).
    """
    raise NotImplementedError(
        "load_all() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )


def get_config() -> Dict[str, Any]:
    """Retrieve global simulation configuration and parameter boundaries.

    Returns
    -------
    dict
        Dictionary loaded from config.json with keys:
        - contract_version : str (e.g. "1.0")
        - grid : dict with "rows" (64), "cols" (64), "cell_size_m" (40)
        - time : dict with "dt_s" (60), "horizon_steps" (120)
        - wet_threshold_m : float (0.05)
        - params : dict of min/max/default ranges for simulation parameters

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4.
    """
    raise NotImplementedError(
        "get_config() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )


def get_terrain() -> Dict[str, Any]:
    """Retrieve static elevation data and spatial metadata.

    Returns
    -------
    dict
        Dictionary containing terrain elevation grid and spatial bounds:
        - elevation : list[list[float]] of shape 64 x 64 (meters above sea level)
                      row 0 = north, col 0 = west
        - dx_m : float, cell resolution in meters (40.0)
        - bounds : list[float], geographic [min_lat, min_lon, max_lat, max_lon]
        - shape : list[int], [64, 64]
        - min_elevation : float (meters)
        - max_elevation : float (meters)

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 1 (Terrain ingestion).
    """
    raise NotImplementedError(
        "get_terrain() is not implemented yet (Phase 1). Use hydrovision_ml.mock for mock testing."
    )


def forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute fast neural surrogate inference to predict water depth evolution.

    Parameters
    ----------
    params : dict
        Simulation parameters:
        - rain_intensity_mmhr : float, peak rainfall intensity [20, 150]
        - rain_duration_min : float, rainfall storm duration [15, 90]
        - rain_shape : str, hyetograph shape ("constant" | "triangular" | "double_peak")
        - drain_capacity_mmhr : float, urban storm drain infiltration [0, 30]
        - horizon_steps : int, number of simulation steps [10, 120] (default 120)

    Returns
    -------
    dict
        Forecast output matching CONTRACT.md schema:
        - times_s : list[int] of length 121 (0, 60, 120, ..., 7200 seconds)
        - depth_frames : list[list[list[float]]] of shape 121 x 64 x 64
                         Water depth in meters (non-negative, row 0 = north, col 0 = west)
        - rain_series_mmhr : list[float] of length 120
        - peak_depth_m : float, maximum water depth observed across all cells and frames
        - flooded_area_m2 : float, total area in square meters exceeding wet_threshold_m (0.05m)
        - inference_time_ms : float, wall-clock neural surrogate rollout execution time
        - model_name : str, surrogate model identifier (e.g. "unet-surrogate-v1")

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4 (Surrogate model).
    """
    raise NotImplementedError(
        "forecast() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )


def forecast_batch(params_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute batched neural surrogate inference across multiple rainfall scenarios.

    Parameters
    ----------
    params_list : list[dict]
        List of scenario parameter dictionaries, each formatted as required by forecast().

    Returns
    -------
    dict
        Dictionary containing:
        - batch : list[dict], each being a full forecast result dictionary
        - total_inference_time_ms : float

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4.
    """
    raise NotImplementedError(
        "forecast_batch() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )


def run_solver(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute high-fidelity 2D Shallow Water Equations (SWE) numerical solver.

    Parameters
    ----------
    params : dict
        Identical parameter dictionary as passed to forecast().

    Returns
    -------
    dict
        Numerical solver ground-truth output:
        - times_s : list[int] of length 121 (0, 60, ..., 7200 seconds)
        - depth_frames : list[list[list[float]]] of shape 121 x 64 x 64 (depth in meters)
        - rain_series_mmhr : list[float] of length 120
        - peak_depth_m : float, maximum water depth in meters
        - solve_time_s : float, numerical solver wall-clock execution time
        - solver_name : str, solver algorithm identifier (e.g. "swe-local-inertial")

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 2 (Numerical solver).
    """
    raise NotImplementedError(
        "run_solver() is not implemented yet (Phase 2). Use hydrovision_ml.mock for mock testing."
    )


def compute_metrics(
    surrogate_frames: Any,
    solver_frames: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute verification metrics comparing surrogate forecast against numerical ground truth.

    Parameters
    ----------
    surrogate_frames : array-like or list
        Depth frames predicted by surrogate of shape 121 x 64 x 64 (or N frames x 64 x 64).
    solver_frames : array-like or list
        Depth frames computed by numerical solver of matching shape.
    params : dict
        Scenario parameters used during simulation.

    Returns
    -------
    dict
        Formal evaluation metrics matching CONTRACT.md Section 5:
        - mae : float, Mean Absolute Error in meters across all wet/dry grid cells
        - rmse : float, Root Mean Squared Error in meters
        - peak_depth_error : float, absolute discrepancy in peak water depth |max(pred) - max(true)|
        - wet_iou : float, Intersection-over-Union for cells exceeding wet_threshold_m (0.05m)
        - mass_error : float, relative mass conservation discrepancy |Vol_pred - Vol_true| / Vol_true
        - arrival_time_error_s : float, difference in wetting front arrival time in seconds
        - speedup : float, ratio of solver runtime to surrogate inference runtime (e.g. 150.0x)

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 6 (Evaluation suite).
    """
    raise NotImplementedError(
        "compute_metrics() is not implemented yet (Phase 6). Use hydrovision_ml.mock for mock testing."
    )


def get_model_info() -> Dict[str, Any]:
    """Retrieve metadata about the currently active surrogate model checkpoint.

    Returns
    -------
    dict
        Model metadata:
        - model_name : str
        - is_mock : bool
        - device : str ("cpu" | "cuda" | "mps")
        - checkpoint_path : str
        - contract_version : str ("1.0")
        - parameters_count : int

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4.
    """
    raise NotImplementedError(
        "get_model_info() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )

