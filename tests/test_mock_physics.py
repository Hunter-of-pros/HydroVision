"""Unit tests for physically based mock simulation physics and mass conservation.

Validates:
- Check a: Mass budget residual strictly < 1e-6 across scenarios.
- Check b: Downhill flow on a tilted plane (no uphill flow) and central bowl pooling.
- Check c: Monotonic volume rise during rain, post-rain volume conservation/drainage,
          and upslope cell drying.
- Check d: Drain effect (drain > 0 yields strictly lower volume than drain == 0).
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from hydrovision_ml import mock
from hydrovision_ml.config import CELL_SIZE_M, COLS, DT_S, HORIZON_STEPS, ROWS, WET_THRESHOLD_M
from hydrovision_ml.solver.scenarios import make_rain_series


def test_mass_budget_exactness_across_presets():
    """Verify maximum mass residual is strictly under 1e-6 for all presets."""
    scenarios = [
        {"rain_intensity_mmhr": 60.0, "rain_duration_min": 45.0, "rain_shape": "constant", "drain_capacity_mmhr": 0.0},
        {"rain_intensity_mmhr": 120.0, "rain_duration_min": 30.0, "rain_shape": "triangular", "drain_capacity_mmhr": 5.0},
        {"rain_intensity_mmhr": 80.0, "rain_duration_min": 45.0, "rain_shape": "constant", "drain_capacity_mmhr": 25.0},
        {"rain_intensity_mmhr": 20.0, "rain_duration_min": 15.0, "rain_shape": "constant", "drain_capacity_mmhr": 0.0},
        {"rain_intensity_mmhr": 150.0, "rain_duration_min": 90.0, "rain_shape": "constant", "drain_capacity_mmhr": 30.0},
    ]

    for p in scenarios:
        res = mock.forecast(p)
        residuals = res["mass_residual_series"]
        assert all(math.isfinite(r) for r in residuals)
        max_res = max(residuals)
        assert max_res < 1e-6, f"Scenario {p} residual {max_res} exceeded 1e-6"


def test_tilted_plane_downhill_flow():
    """Verify water on a tilted plane moves downhill and pools at the lower cells."""
    r_idx, c_idx = np.indices((ROWS, COLS))
    # Tilted plane descending from West (col 0, 100m) to East (col 63, 87.4m)
    plane_dem = 100.0 - 0.2 * c_idx

    frames, _, budget, _ = mock._run_hydrodynamic_simulation(
        params={
            "rain_intensity_mmhr": 80.0,
            "rain_duration_min": 30.0,
            "rain_shape": "constant",
            "drain_capacity_mmhr": 0.0,
            "horizon_steps": 60,
        },
        custom_dem=plane_dem,
    )

    # Frame 30 is at the end of the 30-min rain
    # Frame 60 is 30 mins after rain stopped
    west_upslope_rain_end = float(np.mean(frames[30, :, 0:10]))
    west_upslope_final = float(np.mean(frames[-1, :, 0:10]))

    east_downslope_rain_end = float(np.mean(frames[30, :, 54:64]))
    east_downslope_final = float(np.mean(frames[-1, :, 54:64]))

    # 1. Upslope cells dry out after rain stops
    assert west_upslope_final < west_upslope_rain_end, "Upslope cells must drain after rain stops"

    # 2. Downslope cells accumulate water
    assert east_downslope_final > east_downslope_rain_end, "Downslope cells must accumulate runoff"

    # 3. Final water at the lowest edge is much greater than at the highest edge
    assert east_downslope_final > 3.0 * west_upslope_final, "Water must pool predominantly at lowest edge"

    # 4. Mass conservation is exact
    max_res = max(budget["mass_residual_series"])
    assert max_res < 1e-6, f"Tilted plane mass residual {max_res} must be < 1e-6"


def test_central_bowl_pooling():
    """Verify water in a symmetrical bowl pools in the central basin."""
    r_idx, c_idx = np.indices((ROWS, COLS))
    dist_center_sq = (r_idx - 32) ** 2 + (c_idx - 32) ** 2
    bowl_dem = 100.0 - 8.0 * np.exp(-dist_center_sq / (2.0 * (8.0 ** 2)))

    frames, _, budget, _ = mock._run_hydrodynamic_simulation(
        params={
            "rain_intensity_mmhr": 80.0,
            "rain_duration_min": 30.0,
            "rain_shape": "constant",
            "drain_capacity_mmhr": 0.0,
            "horizon_steps": 60,
        },
        custom_dem=bowl_dem,
    )

    center_depth_final = float(np.mean(frames[-1, 30:35, 30:35]))
    rim_depth_final = float(np.mean(frames[-1, 0:10, 0:10]))

    # Center must retain much more water than high rim
    assert center_depth_final > 10.0 * rim_depth_final, "Water must pool in central depression"
    assert rim_depth_final < 0.05, "Bowl rim should drain and remain shallow"

    max_res = max(budget["mass_residual_series"])
    assert max_res < 1e-6, f"Bowl mass residual {max_res} must be < 1e-6"


def test_volume_monotonic_during_rain_and_flat_post_rain():
    """Verify total volume rises monotonically during rain and stays flat with 0 drain."""
    res = mock.forecast({
        "rain_intensity_mmhr": 60.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    })

    vols = res["volume_m3_series"]
    # During rain (step 1 to 45), volume must increase strictly
    for t in range(1, 46):
        assert vols[t] > vols[t - 1], f"Volume at step {t} must be strictly greater than step {t-1}"

    # After rain stops (step 45 to 120) with drain=0, volume must remain constant (closed boundaries)
    for t in range(46, 121):
        assert abs(vols[t] - vols[45]) < 1.0, f"Volume at step {t} must remain flat within 1m3 (got {vols[t]} vs {vols[45]})"


def test_drain_capacity_effect():
    """Verify non-zero drain capacity strictly reduces total flood volume."""
    res_no_drain = mock.forecast({
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    })

    res_with_drain = mock.forecast({
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 15.0,
        "horizon_steps": 120,
    })

    vol_no_drain = res_no_drain["total_volume_m3"]
    vol_with_drain = res_with_drain["total_volume_m3"]

    assert vol_with_drain < vol_no_drain, "Drain capacity must reduce final flood volume"
    assert vol_with_drain < 0.8 * vol_no_drain, "15mm/hr drain should reduce volume by at least 20%"
