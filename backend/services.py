"""Service orchestration layer for HydroVision backend.

Bridges FastAPI endpoint routes to the underlying hydrovision_ml package.
Selects mock or real execution based on the HYDRO_MODE environment variable.

Owner: Backend (Vikas)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import HTTPException

# Environment mode: "mock" (default) or "real"
def get_hydro_mode() -> str:
    """Return the active HYDRO_MODE setting ('mock' or 'real')."""
    return os.getenv("HYDRO_MODE", "mock").lower()


def is_mock_mode() -> bool:
    """Check if the backend is operating in mock mode."""
    return get_hydro_mode() != "real"


def get_ml_module():
    """Dynamically return the active ML module based on current HYDRO_MODE."""
    if is_mock_mode():
        import hydrovision_ml.mock as m
        return m
    else:
        import hydrovision_ml.api as a
        return a


def get_health() -> Dict[str, Any]:
    """Retrieve operational health and model status for both mock and real modes."""
    ml = get_ml_module()
    mock_active = is_mock_mode()
    model_loaded = False
    contract_ver = "1.0"
    try:
        info = ml.get_model_info()
        mock_active = bool(info.get("is_mock", mock_active))
        model_loaded = True
        contract_ver = str(info.get("contract_version", "1.0"))
    except Exception:
        # In real mode when weights are not yet loaded, model_loaded is False
        model_loaded = False

    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "is_mock": mock_active,
        "contract_version": contract_ver,
    }


def get_config() -> Dict[str, Any]:
    """Retrieve configuration dictionary loaded from config.json."""
    return get_ml_module().get_config()


def get_terrain() -> Dict[str, Any]:
    """Retrieve digital elevation model and geographic bounds."""
    return get_ml_module().get_terrain()


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
    ml = get_ml_module()
    stride = int(params.get("frame_stride", 1))
    result = ml.forecast(params)
    if "model_name" not in result:
        result["model_name"] = "mock-v0" if is_mock_mode() else "unet-surrogate-v1"

    if stride > 1:
        result["times_s"] = result["times_s"][::stride]
        result["depth_frames"] = result["depth_frames"][::stride]
        for key in [
            "volume_m3_series",
            "cum_rain_m3_series",
            "cum_drain_m3_series",
            "cum_outflow_m3_series",
            "mass_residual_series",
        ]:
            if key in result and isinstance(result[key], list):
                result[key] = result[key][::stride]
        result["frame_stride"] = stride
    else:
        result["frame_stride"] = 1
    return result


def compare(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute both surrogate and numerical solver, computing comparative metrics."""
    ml = get_ml_module()
    stride = int(params.get("frame_stride", 1))
    surr_res = ml.forecast(params)
    if "model_name" not in surr_res:
        surr_res["model_name"] = "mock-v0" if is_mock_mode() else "unet-surrogate-v1"

    solv_res = ml.run_solver(params)
    metrics = ml.compute_metrics(
        surrogate_frames=surr_res["depth_frames"],
        solver_frames=solv_res["depth_frames"],
        params=params,
    )

    if stride > 1:
        surr_res["times_s"] = surr_res["times_s"][::stride]
        surr_res["depth_frames"] = surr_res["depth_frames"][::stride]
        solv_res["times_s"] = solv_res["times_s"][::stride]
        solv_res["depth_frames"] = solv_res["depth_frames"][::stride]
        for key in [
            "volume_m3_series",
            "cum_rain_m3_series",
            "cum_drain_m3_series",
            "cum_outflow_m3_series",
            "mass_residual_series",
        ]:
            if key in surr_res and isinstance(surr_res[key], list):
                surr_res[key] = surr_res[key][::stride]
            if key in solv_res and isinstance(solv_res[key], list):
                solv_res[key] = solv_res[key][::stride]

        if "mae_series" in metrics and isinstance(metrics["mae_series"], list):
            metrics["mae_series"] = metrics["mae_series"][::stride]
        if "mass_residual_series" in metrics and isinstance(metrics["mass_residual_series"], list):
            metrics["mass_residual_series"] = metrics["mass_residual_series"][::stride]
        if "solver_mass_residual_series" in metrics and isinstance(metrics["solver_mass_residual_series"], list):
            metrics["solver_mass_residual_series"] = metrics["solver_mass_residual_series"][::stride]

        surr_res["frame_stride"] = stride
        solv_res["frame_stride"] = stride
    else:
        surr_res["frame_stride"] = 1
        solv_res["frame_stride"] = 1

    return {
        "surrogate": surr_res,
        "solver": solv_res,
        "metrics": metrics,
        "model_name": surr_res.get("model_name", "mock-v0"),
    }


def get_eval_results() -> Dict[str, Any]:
    """Retrieve empirical evaluation benchmark results.

    Serves results/eval_summary.json if it exists; otherwise serves results/eval_summary.mock.json
    with is_mock=True. Returns HTTP 404 only if neither exists.
    """
    repo_root = Path(__file__).resolve().parent.parent
    real_path = repo_root / "results" / "eval_summary.json"
    mock_path = repo_root / "results" / "eval_summary.mock.json"

    if real_path.exists():
        try:
            with open(real_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # Fallback to mock file on corrupt real file

    if mock_path.exists():
        try:
            with open(mock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["is_mock"] = True
                return data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read mock evaluation results: {e}")

    raise HTTPException(status_code=404, detail="Evaluation summary results not found.")


