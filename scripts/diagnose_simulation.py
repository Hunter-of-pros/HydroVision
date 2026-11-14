"""Comprehensive diagnostic script for HydroVision simulation physics and rendering checks.

Implements all diagnostic checks specified in Step 1:
- Checks (a) to (g) across:
  1. Preset 1: Moderate Summer Storm (60 mm/hr, 45 min, const, 0 drain)
  2. Preset 2: Extreme Cloudburst (120 mm/hr, 30 min, tri, 5 drain)
  3. Preset 3: Mitigated Retention Test (80 mm/hr, 45 min, const, 25 drain)
  4. Min Case: (20 mm/hr, 15 min, const, 0 drain)
  5. Max Case: (150 mm/hr, 90 min, const, 30 drain)
  6. Controlled Test 1: Tilted Plane (unidirectional slope)
  7. Controlled Test 2: Symmetrical Bowl (central depression)
- Tests both current mock engine (hydrovision_ml.mock) and teammate's solver (hydrovision_ml.solver.swe_solver).
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any, Dict, List, Tuple

import numpy as np

import hydrovision_ml.mock as mock_engine
from hydrovision_ml.config import CELL_SIZE_M, COLS, DT_S, HORIZON_STEPS, ROWS, WET_THRESHOLD_M
from hydrovision_ml.solver.scenarios import make_rain_series
from hydrovision_ml.solver.swe_solver import run_solver_core


def run_checks_for_frames(
    frames: np.ndarray, # (num_frames, rows, cols)
    rain_series_mmhr: List[float],
    drain_capacity_mmhr: float,
    dem: np.ndarray,
    dx: float = CELL_SIZE_M,
    dt: float = float(DT_S),
    name: str = "Test",
) -> Dict[str, Any]:
    num_frames, rows, cols = frames.shape
    cell_area = dx * dx
    total_area = rows * cols * cell_area

    # a. Mass budget check
    # cumulative rain volume over time
    rain_rates_mps = [r / (1000.0 * 3600.0) for r in rain_series_mmhr]
    drain_rate_mps = drain_capacity_mmhr / (1000.0 * 3600.0)

    cum_rain_m3 = 0.0
    cum_drain_m3 = 0.0
    max_mass_residual = 0.0
    mass_residuals = []

    actual_vols = []
    expected_vols = []

    for t in range(num_frames):
        actual_vol = float(np.sum(frames[t]) * cell_area)
        actual_vols.append(actual_vol)

        if t > 0:
            step_idx = t - 1
            r_rate = rain_rates_mps[step_idx] if step_idx < len(rain_rates_mps) else 0.0
            cum_rain_m3 += r_rate * dt * total_area
            # drain bounded by available volume
            drain_pot = drain_rate_mps * dt * total_area
            cum_drain_m3 += min(actual_vol, drain_pot)

        expected_vol = max(0.0, cum_rain_m3 - cum_drain_m3)
        expected_vols.append(expected_vol)

        if cum_rain_m3 > 1e-4:
            res = abs(actual_vol - expected_vol) / cum_rain_m3
        else:
            res = 0.0
        mass_residuals.append(res)
        if res > max_mass_residual:
            max_mass_residual = res

    # c. During rain monotonic rise vs after rain stops
    # Find when rain stops
    rain_end_step = 0
    for idx, r in enumerate(rain_series_mmhr):
        if r > 0.01:
            rain_end_step = idx + 1

    rain_vols = actual_vols[:rain_end_step + 1]
    post_rain_vols = actual_vols[rain_end_step:]

    # Check if volume rises monotonically during rain (with drain=0)
    rain_rises_monotonically = True
    for i in range(1, len(rain_vols)):
        if drain_capacity_mmhr == 0.0 and rain_vols[i] < rain_vols[i - 1] - 1e-5:
            rain_rises_monotonically = False
            break

    # After rain stops: flat (if drain=0) or falling (if drain>0)
    post_rain_behavior_pass = True
    post_rain_flat_or_falling = True
    for i in range(1, len(post_rain_vols)):
        if drain_capacity_mmhr == 0.0:
            if abs(post_rain_vols[i] - post_rain_vols[i - 1]) > 1e-2 * (post_rain_vols[0] + 1e-5):
                post_rain_flat_or_falling = False
        else:
            if post_rain_vols[i] > post_rain_vols[i - 1] + 1e-5:
                post_rain_flat_or_falling = False

    # Check if shallow upslope cells dry out while basins retain water
    # Compare Frame at rain_end vs final frame
    high_cells = dem > np.percentile(dem, 75)
    low_cells = dem < np.percentile(dem, 25)

    high_dry_change = np.mean(frames[-1][high_cells]) - np.mean(frames[rain_end_step][high_cells])
    low_pool_change = np.mean(frames[-1][low_cells]) - np.mean(frames[rain_end_step][low_cells])

    upslope_dries = high_dry_change <= 0.0

    # e. Wet front speed: cells per 60s frame
    wet_masks = frames >= WET_THRESHOLD_M
    wet_front_speeds = [] # cells per frame
    teleport_detected = False

    for t in range(1, num_frames):
        prev_wet = wet_masks[t - 1]
        curr_wet = wet_masks[t]
        newly_wet = curr_wet & (~prev_wet)
        if np.any(newly_wet) and np.any(prev_wet):
            # calculate minimum distance from newly wet cells to nearest previously wet cell
            prev_coords = np.argwhere(prev_wet)
            new_coords = np.argwhere(newly_wet)
            # Sample distances to avoid O(N^2) explosion
            if len(new_coords) > 200:
                sample_idx = np.random.choice(len(new_coords), 200, replace=False)
                new_coords = new_coords[sample_idx]
            dists = []
            for nc in new_coords:
                d = np.min(np.sqrt(np.sum((prev_coords - nc) ** 2, axis=1)))
                dists.append(d)
            max_advance_cells = float(np.max(dists)) if dists else 0.0
            wet_front_speeds.append(max_advance_cells)
            if max_advance_cells > 5.0: # 5 cells * 60.9m = 304m in 60s -> 5 m/s
                teleport_detected = True
        elif np.any(newly_wet) and not np.any(prev_wet):
            # First wet frame
            wet_count = np.sum(curr_wet)
            # If large area instantly becomes wet (>100 cells across grid), it's teleportation / instantaneous uniform depth
            if wet_count > 50:
                wet_front_speeds.append(float(np.sqrt(wet_count)))
                teleport_detected = True

    max_wet_speed = max(wet_front_speeds) if wet_front_speeds else 0.0

    # f. Artifacts
    has_nan = bool(np.isnan(frames).any())
    has_negative = bool((frames < -1e-6).any())
    min_val = float(np.min(frames))
    max_val = float(np.max(frames))

    # Checkerboard test: Laplacian variance on final frame
    final_frame = frames[-1]
    # high frequency laplacian
    lap = (
        final_frame[:-2, 1:-1]
        + final_frame[2:, 1:-1]
        + final_frame[1:-1, :-2]
        + final_frame[1:-1, 2:]
        - 4 * final_frame[1:-1, 1:-1]
    )
    checkerboard_var = float(np.var(lap))

    # Flicker test: frame-to-frame second derivative variance
    flicker_score = 0.0
    if num_frames >= 3:
        frame_diffs = np.diff(actual_vols)
        frame_accel = np.diff(frame_diffs)
        flicker_score = float(np.std(frame_accel))

    return {
        "name": name,
        "max_mass_residual": max_mass_residual,
        "mass_budget_pass": max_mass_residual < 1e-4,
        "rain_rises_monotonically": rain_rises_monotonically,
        "post_rain_flat_or_falling": post_rain_flat_or_falling,
        "upslope_dries": upslope_dries,
        "max_wet_speed_cells": max_wet_speed,
        "teleport_detected": teleport_detected,
        "has_nan": has_nan,
        "has_negative": has_negative,
        "min_depth": min_val,
        "max_depth": max_val,
        "final_vol_m3": actual_vols[-1],
        "checkerboard_var": checkerboard_var,
        "flicker_score": flicker_score,
    }


def main():
    print("=" * 80)
    print("HYDROVISION SIMULATION DIAGNOSTIC SUITE (STEP 1: ZERO CODE EDITS)")
    print("=" * 80)

    # 1. Identify active generator
    print("\n--- 1. ACTIVE RUNTIME GENERATOR IDENTIFICATION ---")
    print(f"Backend environment HYDRO_MODE: '{mock_engine._MOCK_LOADED}' in mock.py")
    print("Active Frame Producer: hydrovision_ml/mock.py -> _simulate_water_spread()")
    print("Underlying algorithm in mock.py: Static weighting: (max_elev - dem)^2.2 * 3.5 / sum(...)")
    print("Real model in hydrovision_ml/api.py: Raises NotImplementedError (no weights in artifacts/models/)")

    presets = [
        {
            "id": "preset-1",
            "name": "Moderate Summer Storm",
            "params": {
                "rain_intensity_mmhr": 60.0,
                "rain_duration_min": 45.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 0.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "preset-2",
            "name": "Extreme Cloudburst",
            "params": {
                "rain_intensity_mmhr": 120.0,
                "rain_duration_min": 30.0,
                "rain_shape": "triangular",
                "drain_capacity_mmhr": 5.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "preset-3",
            "name": "Mitigated Retention Test",
            "params": {
                "rain_intensity_mmhr": 80.0,
                "rain_duration_min": 45.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 25.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "min-case",
            "name": "Min Parameters (20 mm/hr, 15 min, 0 drain)",
            "params": {
                "rain_intensity_mmhr": 20.0,
                "rain_duration_min": 15.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 0.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "max-case",
            "name": "Max Parameters (150 mm/hr, 90 min, 30 drain)",
            "params": {
                "rain_intensity_mmhr": 150.0,
                "rain_duration_min": 90.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 30.0,
                "horizon_steps": 120,
            },
        },
    ]

    print("\n--- 2. DIAGNOSTIC RESULTS FOR CURRENT MOCK ENGINE (mock.py) ---")
    mock_results = []
    dem_mock = np.array(mock_engine.get_terrain()["elevation"])

    for p in presets:
        res = mock_engine.forecast(p["params"])
        frames = np.array(res["depth_frames"])
        rain_series = res["rain_series_mmhr"]
        drain = p["params"]["drain_capacity_mmhr"]
        metrics = run_checks_for_frames(
            frames=frames,
            rain_series_mmhr=rain_series,
            drain_capacity_mmhr=drain,
            dem=dem_mock,
            dx=CELL_SIZE_M,
            name=p["name"],
        )
        mock_results.append(metrics)
        print(f"\nScenario: {p['name']}")
        print(f"  - Max Mass Residual: {metrics['max_mass_residual']:.6f} (Pass: {metrics['mass_budget_pass']})")
        print(f"  - Monotonic Rise during rain: {metrics['rain_rises_monotonically']}")
        print(f"  - Post-rain stable/drain behavior: {metrics['post_rain_flat_or_falling']}")
        print(f"  - Upslope cells dry out: {metrics['upslope_dries']}")
        print(f"  - Max Wet Front Speed: {metrics['max_wet_speed_cells']:.1f} cells/frame (Teleport detected: {metrics['teleport_detected']})")
        print(f"  - Negatives / NaNs: Neg={metrics['has_negative']} (min={metrics['min_depth']}), NaN={metrics['has_nan']}")
        print(f"  - Peak Depth: {metrics['max_depth']:.3f} m, Final Volume: {metrics['final_vol_m3']:.1f} m3")
        print(f"  - Flicker Score: {metrics['flicker_score']:.2f}")

    # Drain effect check: preset 1 (0 drain) vs same params with drain = 25
    p1_nodrain = mock_engine.forecast({
        "rain_intensity_mmhr": 60.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    })
    p1_withdrain = mock_engine.forecast({
        "rain_intensity_mmhr": 60.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 25.0,
        "horizon_steps": 120,
    })
    vol_nodrain = np.sum(p1_nodrain["depth_frames"][-1]) * CELL_SIZE_M * CELL_SIZE_M
    vol_withdrain = np.sum(p1_withdrain["depth_frames"][-1]) * CELL_SIZE_M * CELL_SIZE_M
    print("\n--- DRAIN EFFECT CHECK (mock.py) ---")
    print(f"Final Volume without drain: {vol_nodrain:.1f} m3")
    print(f"Final Volume with 25 mm/hr drain: {vol_withdrain:.1f} m3")
    print(f"Drain reduces volume: {vol_withdrain < vol_nodrain} (Difference: {vol_nodrain - vol_withdrain:.1f} m3)")

    # 3. Controlled Synthetic Tests: Tilted Plane and Bowl
    print("\n--- 3. CONTROLLED SYNTHETIC EXPERIMENTS ---")
    # Case A: Tilted Plane (descending West -> East, col 0 -> col 63)
    r_idx, c_idx = np.indices((ROWS, COLS))
    plane_dem = 100.0 - 0.2 * c_idx # row const, west=100m, east=87.4m
    rain_test = make_rain_series(duration_min=30.0, intensity_mmhr=80.0, total_steps=60)

    # Case B: Symmetrical Central Bowl
    dist_center_sq = (r_idx - 32) ** 2 + (c_idx - 32) ** 2
    bowl_dem = 100.0 - 8.0 * np.exp(-dist_center_sq / (2.0 * (8.0 ** 2)))

    # Test how swe_solver.py performs on these!
    print("\nExecuting Teammate's SWE Solver (swe_solver.run_solver_core) on Tilted Plane...")
    t_plane_res = run_solver_core(
        dem=plane_dem,
        rain_series_mmhr=rain_test,
        dt_s=float(DT_S),
        drain_capacity_mmhr=0.0,
        cell_size_m=float(CELL_SIZE_M),
    )
    t_plane_frames = t_plane_res["depth_frames"]
    # Check if water moves downhill (West -> East):
    # col 0 (highest) should have less water at end than col 63 (lowest)
    west_depth_final = float(np.mean(t_plane_frames[-1, :, 0:10]))
    east_depth_final = float(np.mean(t_plane_frames[-1, :, 54:64]))
    west_depth_initial = float(np.mean(t_plane_frames[30, :, 0:10]))
    east_depth_initial = float(np.mean(t_plane_frames[30, :, 54:64]))
    print(f"  Tilted Plane: West (high) depth at t=30min: {west_depth_initial:.4f} m, final t=60min: {west_depth_final:.4f} m")
    print(f"  Tilted Plane: East (low) depth at t=30min: {east_depth_initial:.4f} m, final t=60min: {east_depth_final:.4f} m")
    print(f"  Water flows downhill & drains upslope: {east_depth_final > west_depth_final and west_depth_final < west_depth_initial}")

    # Check mass conservation of swe_solver on tilted plane
    plane_metrics = run_checks_for_frames(
        frames=t_plane_frames,
        rain_series_mmhr=rain_test,
        drain_capacity_mmhr=0.0,
        dem=plane_dem,
        dx=CELL_SIZE_M,
        name="SWE Solver Tilted Plane",
    )
    print(f"  SWE Solver Mass Residual on Tilted Plane: {plane_metrics['max_mass_residual']:.8f}")

    print("\nExecuting Teammate's SWE Solver on Symmetrical Central Bowl...")
    bowl_res = run_solver_core(
        dem=bowl_dem,
        rain_series_mmhr=rain_test,
        dt_s=float(DT_S),
        drain_capacity_mmhr=0.0,
        cell_size_m=float(CELL_SIZE_M),
    )
    bowl_frames = bowl_res["depth_frames"]
    center_depth_final = float(np.mean(bowl_frames[-1, 30:35, 30:35]))
    rim_depth_final = float(np.mean(bowl_frames[-1, 0:10, 0:10]))
    print(f"  Bowl: Center (lowest) final depth: {center_depth_final:.4f} m")
    print(f"  Bowl: Rim (highest) final depth: {rim_depth_final:.4f} m")
    print(f"  Water pools at lowest center cells: {center_depth_final > rim_depth_final * 5}")
    bowl_metrics = run_checks_for_frames(
        frames=bowl_frames,
        rain_series_mmhr=rain_test,
        drain_capacity_mmhr=0.0,
        dem=bowl_dem,
        dx=CELL_SIZE_M,
        name="SWE Solver Central Bowl",
    )
    print(f"  SWE Solver Mass Residual on Central Bowl: {bowl_metrics['max_mass_residual']:.8f}")

    print("\nExecution complete.")

if __name__ == "__main__":
    main()

