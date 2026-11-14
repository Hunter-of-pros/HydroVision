"""Automated test suite for HydroVision ML pipeline (Phases 1, 2, and 6).

Phase: Quality & Contract Assurance
Owner: ML Teammate
"""

import numpy as np
import pytest

from hydrovision_ml.config import CELL_SIZE_M, COLS, HORIZON_STEPS, ROWS
from hydrovision_ml.eval.metrics import (
    arrival_time_error,
    compute_all_metrics,
    mass_balance_relative_error,
    mean_absolute_error,
    peak_depth_error,
    root_mean_square_error,
    wet_iou,
)
from hydrovision_ml.solver.scenarios import make_rain_series, sample_scenarios
from hydrovision_ml.solver.swe_solver import run_solver_core
from hydrovision_ml.terrain.dem import (
    compute_slopes,
    dem_quality_check,
    load_terrain,
    make_synthetic_dem,
    save_terrain,
)


def test_synthetic_dem_generation():
    dem = make_synthetic_dem(rows=ROWS, cols=COLS, cell_size_m=CELL_SIZE_M)
    assert isinstance(dem, np.ndarray)
    assert dem.shape == (64, 64)
    assert not np.any(np.isnan(dem))
    assert not np.any(np.isinf(dem))
    # Check regional slope from NW to SE
    assert dem[0, 0] > dem[63, 63]
    # Check QA
    qa = dem_quality_check(dem)
    assert qa["is_valid"] is True
    assert qa["nan_count"] == 0
    assert qa["sink_count"] >= 1


def test_slope_computation():
    dem = make_synthetic_dem()
    slope_x, slope_y = compute_slopes(dem, cell_size_m=CELL_SIZE_M)
    assert slope_x.shape == (64, 64)
    assert slope_y.shape == (64, 64)
    assert not np.any(np.isnan(slope_x))
    assert not np.any(np.isnan(slope_y))


def test_terrain_persistence(tmp_path):
    dem = make_synthetic_dem()
    out_file = str(tmp_path / "test_terrain.npz")
    save_terrain(dem, output_path=out_file)

    loaded = load_terrain(out_file)
    assert loaded["shape"] == [64, 64]
    assert loaded["dx_m"] == 40.0
    assert len(loaded["elevation"]) == 64
    assert len(loaded["elevation"][0]) == 64
    assert loaded["min_elevation"] <= loaded["max_elevation"]


def test_rain_series_profiles():
    # Constant
    r_const = make_rain_series(duration_min=30, intensity_mmhr=60.0, shape="constant", total_steps=60)
    assert len(r_const) == 60
    assert r_const[0] == 60.0
    assert r_const[29] == 60.0
    assert r_const[30] == 0.0

    # Triangular
    r_tri = make_rain_series(duration_min=40, intensity_mmhr=80.0, shape="triangular", total_steps=60)
    assert len(r_tri) == 60
    assert r_tri[0] == 0.0
    assert max(r_tri) == pytest.approx(80.0, abs=1.0)
    assert r_tri[40] == 0.0

    # Double peak
    r_dp = make_rain_series(duration_min=60, intensity_mmhr=100.0, shape="double_peak", total_steps=60)
    assert len(r_dp) == 60
    assert max(r_dp) == pytest.approx(100.0, abs=1.0)


def test_sample_scenarios():
    scenarios = sample_scenarios(n=10, seed=123)
    assert len(scenarios) == 10
    for s in scenarios:
        assert 20.0 <= s["rain_intensity_mmhr"] <= 150.0
        assert 15.0 <= s["rain_duration_min"] <= 90.0
        assert s["rain_shape"] in ["constant", "triangular", "double_peak"]
        assert 0.0 <= s["drain_capacity_mmhr"] <= 30.0
        assert s["horizon_steps"] == HORIZON_STEPS


def test_swe_solver_physics():
    dem = make_synthetic_dem()
    rain = make_rain_series(duration_min=20, intensity_mmhr=60.0, shape="constant", total_steps=20)
    res = run_solver_core(dem=dem, rain_series_mmhr=rain, dt_s=60.0, drain_capacity_mmhr=5.0)

    frames = res["depth_frames"]
    assert frames.shape == (21, 64, 64)
    # Frame 0 must be dry
    assert np.all(frames[0] == 0.0)
    # Non-negativity constraint
    assert np.all(frames >= 0.0)
    assert not np.any(np.isnan(frames))
    # Water must have pooled in retention basins
    assert np.max(frames) > 0.05
    assert res["solve_time_s"] > 0.0


def test_hydrological_metrics():
    # Exact match case
    arr = np.zeros((10, 64, 64), dtype=float)
    arr[:, 30:35, 30:35] = 0.5
    metrics_exact = compute_all_metrics(arr, arr)
    assert metrics_exact["mae"] == 0.0
    assert metrics_exact["rmse"] == 0.0
    assert metrics_exact["peak_depth_error"] == 0.0
    assert metrics_exact["wet_iou"] == 1.0
    assert metrics_exact["mass_error"] == 0.0

    # Perturbed case
    perturbed = arr * 1.1
    metrics_pert = compute_all_metrics(perturbed, arr)
    assert metrics_pert["mae"] > 0.0
    assert metrics_pert["wet_iou"] == 1.0
    assert metrics_pert["peak_depth_error"] == pytest.approx(0.05, abs=0.01)
