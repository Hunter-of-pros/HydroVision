"""Test that hydrovision_ml.mock strictly obeys the shapes and bounds of docs/CONTRACT.md.

Phase: Quality & Contract Assurance
"""

import math
import numpy as np
import pytest

from hydrovision_ml import mock


def test_mock_get_terrain():
    terrain = mock.get_terrain()
    assert isinstance(terrain, dict)
    elevation = terrain["elevation"]
    assert len(elevation) == 64
    assert len(elevation[0]) == 64
    assert terrain["dx_m"] == 40.0
    assert len(terrain["bounds"]) == 4
    assert terrain["shape"] == [64, 64]
    assert terrain["min_elevation"] <= terrain["max_elevation"]


def test_mock_forecast_shapes_and_values():
    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    result = mock.forecast(params)

    # Required keys per CONTRACT.md
    for key in [
        "times_s",
        "depth_frames",
        "rain_series_mmhr",
        "peak_depth_m",
        "flooded_area_m2",
        "inference_time_ms",
        "model_name",
    ]:
        assert key in result, f"Missing key '{key}' in forecast output"

    times = result["times_s"]
    assert len(times) == 121
    assert times[0] == 0
    assert times[-1] == 120 * 60

    rain = result["rain_series_mmhr"]
    assert len(rain) == 120

    frames = result["depth_frames"]
    assert len(frames) == 121

    # Check frame 0 is all zeros (dry initial state)
    frame_0 = np.array(frames[0])
    assert frame_0.shape == (64, 64)
    assert np.all(frame_0 == 0.0), "Frame 0 at t=0 must be dry (depth 0.0 everywhere)"

    # Check final frame
    arr = np.array(frames)
    assert arr.shape == (121, 64, 64)
    assert np.all(arr >= 0.0), "Water depth must never be negative"
    assert not np.any(np.isnan(arr)), "Water depth must not contain NaN"
    assert not np.any(np.isinf(arr)), "Water depth must not contain Inf"

    # Max depth check
    assert result["peak_depth_m"] >= 0.0
    assert result["flooded_area_m2"] >= 0.0
    assert result["inference_time_ms"] > 0.0
    assert result["model_name"] == "mock-v0"


def test_mock_solver_execution():
    params = {
        "rain_intensity_mmhr": 60.0,
        "rain_duration_min": 30.0,
        "horizon_steps": 10,  # Fast run for unit tests
    }
    # Using small horizon_steps for test speed
    res = mock.run_solver(params)
    assert len(res["times_s"]) == 11
    assert len(res["depth_frames"]) == 11
    assert res["solve_time_s"] > 0.0
    assert "swe" in res["solver_name"]


def test_mock_compute_metrics():
    # Synthetic predictions and targets
    pred = np.zeros((121, 64, 64), dtype=float)
    solv = np.zeros((121, 64, 64), dtype=float)
    # Add a small puddle to both
    pred[:, 40:45, 40:45] = 0.5
    solv[:, 40:45, 40:45] = 0.48

    metrics = mock.compute_metrics(pred.tolist(), solv.tolist(), params={})

    expected_keys = [
        "mae",
        "rmse",
        "peak_depth_error",
        "wet_iou",
        "mass_error",
        "arrival_time_error_s",
        "speedup",
    ]
    for k in expected_keys:
        assert k in metrics, f"Missing metric key '{k}'"
        assert isinstance(metrics[k], (int, float))
        assert not math.isnan(metrics[k])

    assert metrics["wet_iou"] == 1.0  # Exactly same puddle cells


def test_mock_model_info():
    info = mock.get_model_info()
    assert info["is_mock"] is True
    assert info["model_name"] == "mock-v0"
    assert info["contract_version"] == "1.0"


def test_mock_conservation_series_shapes_and_residuals():
    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    result = mock.forecast(params)

    # 1. Shapes of all new series on forecast are 121 long
    for key in [
        "volume_m3_series",
        "cum_rain_m3_series",
        "cum_drain_m3_series",
        "cum_outflow_m3_series",
        "mass_residual_series",
    ]:
        assert key in result, f"Missing key '{key}' in forecast output"
        assert len(result[key]) == 121, f"Key '{key}' expected length 121, got {len(result[key])}"
        assert all(math.isfinite(v) for v in result[key]), f"Key '{key}' contains non-finite values"

    # 2. Residual is finite and >= 0
    residuals = result["mass_residual_series"]
    assert residuals[0] == 0.0, "Frame 0 residual must be 0.0"
    assert all(r >= 0.0 for r in residuals), "Mass residuals must be non-negative"

    # 3. Solver conservation check (mock solver residual strictly below 1e-6)
    solver_params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "horizon_steps": 120,
    }
    solv_res = mock.run_solver(solver_params)
    for key in [
        "volume_m3_series",
        "cum_rain_m3_series",
        "cum_drain_m3_series",
        "cum_outflow_m3_series",
        "mass_residual_series",
    ]:
        assert key in solv_res
        assert len(solv_res[key]) == 121

    solv_residuals = solv_res["mass_residual_series"]
    assert all(math.isfinite(r) and r >= 0.0 for r in solv_residuals)
    max_solv_residual = max(solv_residuals)
    assert max_solv_residual < 1e-6, f"Mock solver residual {max_solv_residual} must be below 1e-6"

    # 4. Compare metrics contain new v1.1 fields
    metrics = mock.compute_metrics(
        result["depth_frames"],
        solv_res["depth_frames"],
        params=params,
    )
    assert "mae_series" in metrics
    assert len(metrics["mae_series"]) == 121
    assert all(math.isfinite(v) and v >= 0.0 for v in metrics["mae_series"])

    assert "mass_residual_series" in metrics
    assert len(metrics["mass_residual_series"]) == 121
    assert all(math.isfinite(v) and v >= 0.0 for v in metrics["mass_residual_series"])

    assert "solver_mass_residual_series" in metrics
    assert len(metrics["solver_mass_residual_series"]) == 121
    assert max(metrics["solver_mass_residual_series"]) < 1e-6

    assert "peak_extent_iou" in metrics
    assert 0.0 <= metrics["peak_extent_iou"] <= 1.0


