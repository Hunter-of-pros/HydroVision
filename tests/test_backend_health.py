"""Test FastAPI backend endpoints using starlette/fastapi TestClient.

Phase: Quality & Contract Assurance
Owner: Backend (Vikas)
"""

from fastapi.testclient import TestClient
import pytest

from backend.app import app

client = TestClient(app)


def test_health_endpoint_mock():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["is_mock"] is True
    assert data["contract_version"] == "1.0"


def test_health_endpoint_real_mode(monkeypatch):
    monkeypatch.setenv("HYDRO_MODE", "real")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["is_mock"] is False
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
    assert "volume_m3_series" in data
    assert len(data["volume_m3_series"]) == 5
    assert "mass_residual_series" in data


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
    assert "mae_series" in data["metrics"]
    assert "mass_residual_series" in data["metrics"]
    assert "peak_extent_iou" in data["metrics"]
    assert data["model_name"] == "mock-v0"


def test_results_endpoint_mock_fallback():
    response = client.get("/results")
    assert response.status_code == 200
    data = response.json()
    assert data["is_mock"] is True
    assert "hardware" in data
    assert "ablation" in data
    assert len(data["ablation"]) >= 3
    assert "error_vs_horizon" in data
    assert "speedup_scaling" in data
    assert "test_set" in data

    ablation_names = [a["name"] for a in data["ablation"]]
    assert "A plain" in ablation_names
    assert "B mass loss" in ablation_names
    assert "C mass loss + rollout training" in ablation_names


def test_results_endpoint_real_file_precedence(tmp_path, monkeypatch):
    from pathlib import Path
    import json
    import backend.services as services

    # Create dummy real results
    real_data = {
        "generated_at": "2026-11-14T15:00:00Z",
        "hardware": "Mock RTX 4090 Test",
        "is_mock": False,
        "test_set": {"n_runs": 100, "rain_range_mmhr": [20.0, 150.0]},
        "ablation": [
            {"name": "A plain", "mae_m": 0.08, "rmse_m": 0.12, "wet_iou": 0.6, "mass_residual_max": 0.15},
            {"name": "B mass loss", "mae_m": 0.05, "rmse_m": 0.07, "wet_iou": 0.7, "mass_residual_max": 0.03},
            {"name": "C mass loss + rollout training", "mae_m": 0.02, "rmse_m": 0.03, "wet_iou": 0.88, "mass_residual_max": 0.01},
        ],
        "error_vs_horizon": {"steps": [10, 120], "mae_m": [0.005, 0.02]},
        "speedup_scaling": [{"grid": "64x64", "solver_s": 1.5, "surrogate_ms": 38.0}],
    }
    
    # Write real file to real path temporarily
    real_path = Path("results/eval_summary.json")
    real_path.parent.mkdir(parents=True, exist_ok=True)
    with open(real_path, "w", encoding="utf-8") as f:
        json.dump(real_data, f)

    try:
        response = client.get("/results")
        assert response.status_code == 200
        data = response.json()
        assert data["is_mock"] is False
        assert data["hardware"] == "Mock RTX 4090 Test"
    finally:
        if real_path.exists():
            real_path.unlink()


