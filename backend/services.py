"""Service orchestration layer for HydroVision backend.

Bridges FastAPI endpoint routes to the underlying hydrovision_ml package.
Selects mock or real execution based on the HYDRO_MODE environment variable.

Owner: Backend (Vikas)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

# Environment mode: "mock" (default) or "real"
HYDRO_MODE: str = os.getenv("HYDRO_MODE", "mock").lower()

if HYDRO_MODE == "real":
    import hydrovision_ml.api as ml_module
else:
    import hydrovision_ml.mock as ml_module


def is_mock_mode() -> bool:
    """Check if the backend is operating in mock mode."""
    return HYDRO_MODE != "real"


def get_health() -> Dict[str, Any]:
    """Retrieve operational health and model status."""
    info = ml_module.get_model_info()
    return {
        "status": "ok",
        "model_loaded": True,
        "is_mock": bool(info.get("is_mock", is_mock_mode())),
        "contract_version": str(info.get("contract_version", "1.0")),
    }


def get_config() -> Dict[str, Any]:
    """Retrieve configuration dictionary loaded from config.json."""
    return ml_module.get_config()


def get_terrain() -> Dict[str, Any]:
    """Retrieve digital elevation model and geographic bounds."""
    return ml_module.get_terrain()


def get_presets() -> List[Dict[str, Any]]:
    """Return standard demonstration presets for the hackathon UI."""
    return [
        {
            "id": "moderate-summer-storm",
            "name": "Moderate Summer Storm",
            "description": "45-minute continuous rainfall at 60 mm/hr with standard zero-drainage baseline.",
            "params": {
                "rain_intensity_mmhr": 60.0,
                "rain_duration_min": 45.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 0.0,
                "horizon_steps": 120,
                "frame_stride": 1,
            },
        },
        {
            "id": "extreme-cloudburst",
            "name": "Extreme Cloudburst",
            "description": "Severe 120 mm/hr deluge lasting 30 minutes with high stormwater overflow.",
            "params": {
                "rain_intensity_mmhr": 120.0,
                "rain_duration_min": 30.0,
                "rain_shape": "triangular",
                "drain_capacity_mmhr": 5.0,
                "horizon_steps": 120,
                "frame_stride": 1,
            },
        },
        {
            "id": "mitigated-retention-test",
            "name": "Engineered Drain Mitigation",
            "description": "80 mm/hr intense storm counteracted by maximum 25 mm/hr active drainage capacity.",
            "params": {
                "rain_intensity_mmhr": 80.0,
                "rain_duration_min": 45.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 25.0,
                "horizon_steps": 120,
                "frame_stride": 1,
            },
        },
    ]


def forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute neural surrogate forecast rollout."""
    stride = int(params.get("frame_stride", 1))
    result = ml_module.forecast(params)
    if stride > 1:
        result["times_s"] = result["times_s"][::stride]
        result["depth_frames"] = result["depth_frames"][::stride]
        result["frame_stride"] = stride
    else:
        result["frame_stride"] = 1
    return result


def compare(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute both surrogate and numerical solver, computing comparative metrics."""
    stride = int(params.get("frame_stride", 1))
    surr_res = ml_module.forecast(params)
    solv_res = ml_module.run_solver(params)
    metrics = ml_module.compute_metrics(
        surrogate_frames=surr_res["depth_frames"],
        solver_frames=solv_res["depth_frames"],
        params=params,
    )

    if stride > 1:
        surr_res["times_s"] = surr_res["times_s"][::stride]
        surr_res["depth_frames"] = surr_res["depth_frames"][::stride]
        surr_res["frame_stride"] = stride

        solv_res["times_s"] = solv_res["times_s"][::stride]
        solv_res["depth_frames"] = solv_res["depth_frames"][::stride]
        solv_res["frame_stride"] = stride
    else:
        surr_res["frame_stride"] = 1
        solv_res["frame_stride"] = 1

    return {
        "surrogate": surr_res,
        "solver": solv_res,
        "metrics": metrics,
    }

