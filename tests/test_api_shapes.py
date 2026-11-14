"""Contract and shape verification tests for hydrovision_ml.api public interface.

Mirrors the comprehensive acceptance checks in scripts/validate_model.py.
Marked as xfail until the ML teammate implements the respective phase in hydrovision_ml/api.py.
When an API function is implemented, remove its @pytest.mark.xfail decorator.
Do not weaken any check.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from hydrovision_ml import api
from scripts.validate_model import check_forecast_response


@pytest.mark.xfail(reason="Real terrain ingestion scheduled for ML Phase 1", raises=NotImplementedError)
def test_real_api_get_terrain():
    """Verify terrain elevation grid and spatial metadata."""
    terrain = api.get_terrain()
    assert isinstance(terrain, dict), "get_terrain() must return a dictionary"
    
    for key in ["elevation", "dx_m", "bounds", "shape", "min_elevation", "max_elevation"]:
        assert key in terrain, f"Missing terrain key '{key}'"

    elev = np.asarray(terrain["elevation"], dtype=np.float64)
    assert elev.shape == (64, 64), f"Terrain elevation grid must be (64, 64), got {elev.shape}"
    assert terrain["shape"] == [64, 64]
    assert terrain["dx_m"] == 40.0
    assert len(terrain["bounds"]) == 4
    assert terrain["min_elevation"] <= terrain["max_elevation"]
    assert np.all(np.isfinite(elev)), "Terrain elevation must be finite"


@pytest.mark.xfail(reason="Real surrogate model rollout scheduled for ML Phase 4", raises=NotImplementedError)
def test_real_api_forecast():
    """Verify fast neural surrogate rollout against acceptance contract."""
    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    result = api.forecast(params)
    passed, errors, stats = check_forecast_response(
        res=result,
        case_name="real_api_forecast_test",
        max_latency_ms=2000.0,
        residual_threshold=0.05,
    )
    assert passed, f"Surrogate acceptance checks failed: {errors}"


@pytest.mark.xfail(reason="Real hydrodynamic solver scheduled for ML Phase 2", raises=NotImplementedError)
def test_real_api_run_solver():
    """Verify 2D SWE numerical solver against acceptance contract."""
    params = {
        "rain_intensity_mmhr": 60.0,
        "rain_duration_min": 30.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    result = api.run_solver(params)
    for key in ["times_s", "depth_frames", "rain_series_mmhr", "peak_depth_m", "solve_time_s", "solver_name"]:
        assert key in result, f"Missing solver key '{key}'"

    assert len(result["times_s"]) == 121
    assert len(result["rain_series_mmhr"]) == 120
    frames = np.asarray(result["depth_frames"], dtype=np.float64)
    assert frames.shape == (121, 64, 64)
    assert np.all(np.isfinite(frames)), "Solver frames contain non-finite values"
    assert np.min(frames) >= -1e-6, "Solver frames contain negative depths"
    assert np.max(np.abs(frames[0])) <= 1e-6, "Frame 0 must be dry"

    if "mass_residual_series" in result and result["mass_residual_series"] is not None:
        residuals = result["mass_residual_series"]
        assert len(residuals) == 121
        assert max(residuals) <= 0.01, f"Solver mass residual exceeds 0.01: max={max(residuals)}"


@pytest.mark.xfail(reason="Real evaluation suite scheduled for ML Phase 6", raises=NotImplementedError)
def test_real_api_compute_metrics():
    """Verify formal evaluation metric computation against contract."""
    pred = np.zeros((121, 64, 64), dtype=np.float64)
    true = np.zeros((121, 64, 64), dtype=np.float64)
    pred[:, 30:35, 30:35] = 0.5
    true[:, 30:35, 30:35] = 0.48

    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    metrics = api.compute_metrics(pred.tolist(), true.tolist(), params)

    required_metrics = [
        "mae",
        "rmse",
        "peak_depth_error",
        "wet_iou",
        "mass_error",
        "arrival_time_error_s",
        "speedup",
    ]
    for mk in required_metrics:
        assert mk in metrics, f"Missing metric key '{mk}'"
        assert math.isfinite(metrics[mk]), f"Metric '{mk}' must be finite"

    assert 0.0 <= metrics["wet_iou"] <= 1.0


@pytest.mark.xfail(reason="Real model metadata scheduled for ML Phase 4", raises=NotImplementedError)
def test_real_api_get_model_info():
    """Verify model runtime metadata reporting."""
    info = api.get_model_info()
    assert isinstance(info, dict)
    for key in ["model_name", "is_mock", "device", "contract_version"]:
        assert key in info, f"Missing model_info key '{key}'"

    assert info["is_mock"] is False, "Real API must report is_mock=False"
    assert info["contract_version"] == "1.0"
