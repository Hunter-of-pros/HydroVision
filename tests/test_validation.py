"""Validation tests for input parameters, boundary ranges, 422 error messages, and payload rounding.

Owner: Backend (Vikas)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_forecast_rain_intensity_under_min():
    """Verify 422 is returned when rain_intensity_mmhr is below minimum 20 mm/hr."""
    response = client.post("/forecast", json={"rain_intensity_mmhr": 10.0})
    assert response.status_code == 422
    data = response.json()
    assert "rain_intensity_mmhr" in data["detail"]
    assert "greater than or equal to 20" in data["detail"]


def test_forecast_rain_intensity_over_max():
    """Verify 422 is returned when rain_intensity_mmhr exceeds maximum 150 mm/hr."""
    response = client.post("/forecast", json={"rain_intensity_mmhr": 180.0})
    assert response.status_code == 422
    data = response.json()
    assert "rain_intensity_mmhr" in data["detail"]
    assert "less than or equal to 150" in data["detail"]


def test_forecast_rain_duration_out_of_bounds():
    """Verify 422 is returned when rain_duration_min is out of range [15, 90]."""
    res_under = client.post("/forecast", json={"rain_duration_min": 5.0})
    assert res_under.status_code == 422
    assert "rain_duration_min" in res_under.json()["detail"]

    res_over = client.post("/forecast", json={"rain_duration_min": 120.0})
    assert res_over.status_code == 422
    assert "rain_duration_min" in res_over.json()["detail"]


def test_forecast_invalid_rain_shape():
    """Verify 422 is returned when rain_shape is not in allowed list."""
    response = client.post("/forecast", json={"rain_shape": "hurricane"})
    assert response.status_code == 422
    assert "rain_shape" in response.json()["detail"]


def test_forecast_drain_capacity_out_of_bounds():
    """Verify 422 is returned when drain_capacity_mmhr is outside [0, 30]."""
    res_neg = client.post("/forecast", json={"drain_capacity_mmhr": -2.0})
    assert res_neg.status_code == 422
    assert "drain_capacity_mmhr" in res_neg.json()["detail"]

    res_high = client.post("/forecast", json={"drain_capacity_mmhr": 45.0})
    assert res_high.status_code == 422
    assert "drain_capacity_mmhr" in res_high.json()["detail"]


def test_forecast_horizon_steps_out_of_bounds():
    """Verify 422 is returned when horizon_steps is outside [10, 120]."""
    res_low = client.post("/forecast", json={"horizon_steps": 5})
    assert res_low.status_code == 422
    assert "horizon_steps" in res_low.json()["detail"]

    res_high = client.post("/forecast", json={"horizon_steps": 200})
    assert res_high.status_code == 422
    assert "horizon_steps" in res_high.json()["detail"]


def test_compare_endpoint_validation_errors():
    """Verify /compare endpoint validates request parameters and returns 422."""
    response = client.post("/compare", json={"rain_intensity_mmhr": -5.0})
    assert response.status_code == 422
    assert "rain_intensity_mmhr" in response.json()["detail"]


def test_forecast_depth_values_rounded_to_3_decimals():
    """Verify depth_frames in /forecast response are strictly rounded to 3 decimal places."""
    response = client.post(
        "/forecast",
        json={
            "rain_intensity_mmhr": 80.0,
            "rain_duration_min": 45.0,
            "rain_shape": "constant",
            "drain_capacity_mmhr": 0.0,
            "horizon_steps": 120,
            "frame_stride": 10,  # Test a sampled stride
        },
    )
    assert response.status_code == 200
    data = response.json()
    depth_frames = data["depth_frames"]
    assert len(depth_frames) > 0

    for frame in depth_frames:
        for row in frame:
            for depth in row:
                # Every floating point value must match its 3-decimal rounded form
                assert round(depth, 3) == depth

