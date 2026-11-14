"""xfail tests for hydrovision_ml.api public interface.

These tests mark expected failures (xfail) because the real ML surrogate model and solver
are scheduled for implementation by the ML teammate in Phases 1, 2, 4, 5, and 6.

Phase: Quality & Contract Assurance
"""

import pytest

from hydrovision_ml import api


@pytest.mark.xfail(reason="Real terrain ingestion scheduled for Phase 1", raises=NotImplementedError)
def test_real_api_get_terrain():
    terrain = api.get_terrain()
    assert terrain["shape"] == [64, 64]


@pytest.mark.xfail(reason="Real surrogate model scheduled for Phase 4", raises=NotImplementedError)
def test_real_api_forecast():
    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    result = api.forecast(params)
    assert len(result["depth_frames"]) == 121


@pytest.mark.xfail(reason="Real hydrodynamic solver scheduled for Phase 2", raises=NotImplementedError)
def test_real_api_run_solver():
    params = {"rain_intensity_mmhr": 60.0, "rain_duration_min": 30.0}
    result = api.run_solver(params)
    assert "depth_frames" in result


@pytest.mark.xfail(reason="Real evaluation suite scheduled for Phase 6", raises=NotImplementedError)
def test_real_api_compute_metrics():
    metrics = api.compute_metrics([], [], {})
    assert "mae" in metrics


@pytest.mark.xfail(reason="Real model metadata scheduled for Phase 4", raises=NotImplementedError)
def test_real_api_get_model_info():
    info = api.get_model_info()
    assert "model_name" in info

