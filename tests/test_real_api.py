"""Comprehensive unit tests for the production real ML API (hydrovision_ml.api).

Does NOT use starlette TestClient (avoids hang issues).
Tests:
1. Output shapes: depth_frames [121, 64, 64], times_s [121], rain_series [120]
2. Numerical validity: no NaN, non-negative values, frame 0 identically 0.0
3. Determinism: identical outputs across multiple calls with same inputs
4. Batch equivalence: forecast_batch matches single forecast within 1e-5
5. Input validation: ValueError raised on out-of-range parameters
6. Orientation check: verify deepest flood cells correspond to low-elevation areas of DEM (north-up)
7. Agreement with stored solver: compare forecast against stored validation scenario and assert MAE

Phase: Phase 4 & 6 (Wired Real API Verification)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from hydrovision_ml import api
from hydrovision_ml.config import DATA_DIR


@pytest.fixture(scope="module", autouse=True)
def setup_api():
    """Ensure surrogate model and terrain are loaded once for all tests."""
    api.load_all("artifacts/models/best.pt")


def test_forecast_shapes_and_values():
    """Verify forecast returns exact shapes, valid times, and physical depths."""
    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 5.0,
        "horizon_steps": 120,
    }
    res = api.forecast(params)

    # 1. Keys check
    required = [
        "times_s",
        "depth_frames",
        "rain_series_mmhr",
        "peak_depth_m",
        "flooded_area_m2",
        "inference_time_ms",
        "model_name",
    ]
    for k in required:
        assert k in res, f"Missing key: {k}"

    # 2. Times checks
    times = res["times_s"]
    assert len(times) == 121
    assert times[0] == 0
    assert times[-1] == 7200
    assert times == [i * 60 for i in range(121)]

    # 3. Rain series checks
    rain = res["rain_series_mmhr"]
    assert len(rain) == 120
    assert all(r >= 0.0 for r in rain)

    # 4. Depth frames checks
    frames = np.asarray(res["depth_frames"], dtype=np.float32)
    assert frames.shape == (121, 64, 64)
    assert not np.isnan(frames).any(), "Found NaN in depth frames"
    assert not np.isinf(frames).any(), "Found Inf in depth frames"
    assert np.min(frames) >= 0.0, f"Found negative depth: {np.min(frames)}"
    assert np.all(frames[0] == 0.0), f"Frame 0 must be all dry, max={np.max(frames[0])}"

    # 5. Peak depth and flooded area consistency
    assert res["peak_depth_m"] >= 0.0
    assert res["flooded_area_m2"] >= 0.0
    assert res["model_name"] == "unet-surrogate-v1"
    assert res["inference_time_ms"] > 0.0


def test_forecast_determinism():
    """Verify forecast produces bitwise identical predictions for identical inputs."""
    params = {
        "rain_intensity_mmhr": 60.0,
        "rain_duration_min": 30.0,
        "rain_shape": "triangular",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    res1 = api.forecast(params)
    res2 = api.forecast(params)

    f1 = np.asarray(res1["depth_frames"], dtype=np.float32)
    f2 = np.asarray(res2["depth_frames"], dtype=np.float32)
    np.testing.assert_array_equal(f1, f2)


def test_forecast_batch_equivalence():
    """Verify batched rollout matches single-scenario rollouts within 1e-5."""
    p1 = {
        "rain_intensity_mmhr": 50.0,
        "rain_duration_min": 40.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    p2 = {
        "rain_intensity_mmhr": 100.0,
        "rain_duration_min": 60.0,
        "rain_shape": "double_peak",
        "drain_capacity_mmhr": 10.0,
        "horizon_steps": 120,
    }

    single1 = np.asarray(api.forecast(p1)["depth_frames"], dtype=np.float32)
    single2 = np.asarray(api.forecast(p2)["depth_frames"], dtype=np.float32)

    batch_res = api.forecast_batch([p1, p2])
    batch_arr = np.asarray(batch_res["depth_frames"], dtype=np.float32)

    assert batch_arr.shape == (2, 121, 64, 64)
    np.testing.assert_allclose(batch_arr[0], single1, atol=1e-5)
    np.testing.assert_allclose(batch_arr[1], single2, atol=1e-5)


def test_invalid_parameters_raise_value_error():
    """Verify ValueError is raised on out-of-range or malformed parameters."""
    with pytest.raises(ValueError, match="rain_intensity_mmhr"):
        api.forecast({"rain_intensity_mmhr": 5.0})  # min is 20

    with pytest.raises(ValueError, match="rain_intensity_mmhr"):
        api.forecast({"rain_intensity_mmhr": 200.0})  # max is 150

    with pytest.raises(ValueError, match="rain_duration_min"):
        api.forecast({"rain_duration_min": 5.0})  # min is 15

    with pytest.raises(ValueError, match="rain_shape"):
        api.forecast({"rain_shape": "tornado"})

    with pytest.raises(ValueError, match="drain_capacity_mmhr"):
        api.forecast({"drain_capacity_mmhr": -1.0})

    with pytest.raises(ValueError, match="drain_capacity_mmhr"):
        api.forecast({"drain_capacity_mmhr": 50.0})  # max is 30


def test_terrain_orientation_and_flooding_alignment():
    """Verify that deepest flood cells settle in the low-elevation regions of DEM (north-up)."""
    terrain = api.get_terrain()
    dem = np.array(terrain["elevation"], dtype=np.float32)

    params = {
        "rain_intensity_mmhr": 120.0,
        "rain_duration_min": 60.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    res = api.forecast(params)
    final_depth = np.array(res["depth_frames"][-1], dtype=np.float32)

    # Find the top 20 deepest flooded cells
    flat_indices = np.argsort(final_depth.ravel())[::-1][:20]
    deepest_coords = [np.unravel_index(idx, (64, 64)) for idx in flat_indices]

    dem_mean = float(np.mean(dem))
    elevations_at_deepest = [float(dem[r, c]) for r, c in deepest_coords]
    mean_elev_deepest = float(np.mean(elevations_at_deepest))

    print(f"\n[Orientation Check] DEM Mean Elevation: {dem_mean:.2f} m")
    print(f"[Orientation Check] Mean Elevation at 20 Deepest Inundated Cells: {mean_elev_deepest:.2f} m")
    print(f"[Orientation Check] Deepest cell coordinates (row, col): {deepest_coords[:5]}")

    # Physical assertion: water must accumulate in depressions / valleys below average terrain elevation
    assert mean_elev_deepest < dem_mean, (
        f"Deepest flood cells ({mean_elev_deepest:.2f} m) are not below average DEM elevation ({dem_mean:.2f} m)!"
    )


def test_agreement_with_stored_validation_scenario():
    """Verify agreement against stored ground-truth SWE solver for one validation scenario."""
    val_dir = Path(DATA_DIR) / "val"
    if not (val_dir / "depth.npy").exists():
        pytest.skip("Stored validation data not found at DATA_DIR.")

    true_depth_arr = np.load(str(val_dir / "depth.npy"), mmap_mode="r")[0]  # scenario 0
    params_arr = np.load(str(val_dir / "params.npy"))[0]

    params = {
        "rain_intensity_mmhr": float(params_arr[0]),
        "rain_duration_min": float(params_arr[1]),
        "rain_shape": "constant" if int(params_arr[2]) == 0 else ("triangular" if int(params_arr[2]) == 1 else "double_peak"),
        "drain_capacity_mmhr": float(params_arr[3]),
        "horizon_steps": 120,
    }

    res = api.forecast(params)
    pred_depth = np.array(res["depth_frames"], dtype=np.float32)

    mae_m = float(np.mean(np.abs(pred_depth - true_depth_arr)))
    mae_mm = mae_m * 1000.0

    print(f"\n[Validation Agreement] Scenario 0: Rain={params['rain_intensity_mmhr']:.1f} mm/hr, Drain={params['drain_capacity_mmhr']:.1f} mm/hr")
    print(f"[Validation Agreement] 120-Step Rollout MAE: {mae_mm:.2f} mm ({mae_m:.6f} m)")

    # Assert rollout error is below 15 mm for this individual validation scenario
    assert mae_mm < 15.0, f"Rollout MAE {mae_mm:.2f} mm exceeds 15.0 mm threshold"


def test_model_info():
    """Verify model runtime metadata reporting."""
    info = api.get_model_info()
    assert info["model_name"] == "unet-surrogate-v1"
    assert info["is_mock"] is False
    assert info["model_loaded"] is True
    assert info["contract_version"] == "1.0"
    assert info["parameters_count"] > 300_000
    assert "git_commit" in info
