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

