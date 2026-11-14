"""Test FastAPI backend endpoints using starlette/fastapi TestClient.

Phase: Quality & Contract Assurance
Owner: Backend (Vikas)
"""

from fastapi.testclient import TestClient
import pytest

from backend.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["is_mock"] is True
    assert data["contract_version"] == "1.0"


def test_config_endpoint():
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert data["contract_version"] == "1.0"
    assert data["grid"]["rows"] == 64
    assert data["grid"]["cols"] == 64
    assert data["grid"]["cell_size_m"] == 40
    assert data["time"]["dt_s"] == 60
    assert data["time"]["horizon_steps"] == 120
    assert data["wet_threshold_m"] == 0.05
    assert "params" in data


def test_terrain_endpoint_working():
    response = client.get("/terrain")
    assert response.status_code == 200
    data = response.json()
    assert data["shape"] == [64, 64]
    assert len(data["elevation"]) == 64
    assert len(data["elevation"][0]) == 64
    assert data["dx_m"] == 40.0


def test_presets_endpoint_working():
    response = client.get("/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) >= 1
    first = data["presets"][0]
    assert "id" in first
    assert "name" in first
    assert "params" in first


def test_forecast_endpoint_mock_execution():
    payload = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
        "frame_stride": 30,
    }
    response = client.post("/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["times_s"]) == 5  # 121 subsampled with stride 30 = 5 frames
    assert len(data["depth_frames"]) == 5
    assert data["peak_depth_m"] >= 0.0
    assert data["frame_stride"] == 30
    assert data["model_name"] == "mock-v0"


def test_compare_endpoint_mock_execution():
    payload = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 10,  # Fast run for unit test
        "frame_stride": 1,
    }
    response = client.post("/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "surrogate" in data
    assert "solver" in data
    assert "metrics" in data
    assert "speedup" in data["metrics"]
    assert "wet_iou" in data["metrics"]

