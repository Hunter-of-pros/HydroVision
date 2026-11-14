"""2D Shallow Water Equations (SWE) local-inertial numerical solver core.

Solves the de Almeida & Bates (2012) simplified hydrodynamic equations on a 2D regular
grid with Manning friction, infiltration/drainage sink terms, and adaptive CFL time-stepping.

Phase: Phase 2 (Numerical Solver)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from hydrovision_ml.config import (
    CELL_SIZE_M,
    COLS,
    DT_S,
    HORIZON_STEPS,
    ROWS,
    WET_THRESHOLD_M,
)


def run_solver_core(
    dem: np.ndarray,
    rain_series_mmhr: List[float],
    dt_s: float = float(DT_S),
    drain_capacity_mmhr: float = 0.0,
    manning_n: float = 0.035,
    substep_cfl: float = 0.7,
    cell_size_m: float = float(CELL_SIZE_M),
) -> Dict[str, Any]:
    """Execute high-fidelity 2D hydrodynamic simulation over DEM.

    Parameters
    ----------
    dem : np.ndarray
        Elevation field of shape (rows, cols) in meters.
    rain_series_mmhr : list[float]
        Rainfall intensity per macro time step (length = horizon_steps).
    dt_s : float
        Output frame interval in seconds (default: 60.0).
    drain_capacity_mmhr : float
        Uniform infiltration and drainage capacity sink term in mm/hr (default: 0.0).
    manning_n : float
        Surface roughness coefficient (default: 0.035 for urban/vegetated).
    substep_cfl : float
        Courant-Friedrichs-Lewy safety condition multiplier.
    cell_size_m : float
        Spatial resolution in meters (default: 40.0).

    Returns
    -------
    dict
        Solver simulation results:
        - depth_frames : np.ndarray of shape (num_frames, rows, cols)
        - times_s : list[int]
        - max_velocity_frames : np.ndarray of shape (num_frames, rows, cols)
        - solve_time_s : float
    """
    t_start = time.perf_counter()

    dem = np.asarray(dem, dtype=np.float64)
    rows, cols = dem.shape
    dx = float(cell_size_m)
    g = 9.80665  # gravitational acceleration m/s^2
    min_h = 1e-4  # minimum flow depth threshold (0.1 mm)

    total_steps = len(rain_series_mmhr)
    num_frames = total_steps + 1

    # State variables: depth h (rows, cols), discharge qx (rows, cols-1), qy (rows-1, cols)
    h = np.zeros((rows, cols), dtype=np.float64)
    qx = np.zeros((rows, cols - 1), dtype=np.float64)
    qy = np.zeros((rows - 1, cols), dtype=np.float64)

    # Output storage
    depth_frames = np.zeros((num_frames, rows, cols), dtype=np.float32)
    max_velocity_frames = np.zeros((num_frames, rows, cols), dtype=np.float32)
    times_s = [int(step * dt_s) for step in range(num_frames)]
    cum_drain_m3_series = np.zeros(num_frames, dtype=np.float64)

    # Frame 0 is dry initial state
    depth_frames[0] = h.astype(np.float32)

    # Conversion factors: mm/hr -> m/s
    rain_rates_mps = [r / (1000.0 * 3600.0) for r in rain_series_mmhr]
    drain_rate_mps = drain_capacity_mmhr / (1000.0 * 3600.0)

    # Precompute cell elevation differences
    # East-West interfaces: dem[:, :-1] and dem[:, 1:]
    z_w = dem[:, :-1]
    z_e = dem[:, 1:]
    z_max_x = np.maximum(z_w, z_e)

    # North-South interfaces: dem[:-1, :] and dem[1:, :]
    z_n = dem[:-1, :]
    z_s = dem[1:, :]
    z_max_y = np.maximum(z_n, z_s)

    cum_drain_m3 = 0.0
    for step_idx in range(total_steps):
        r_rate = rain_rates_mps[step_idx]
        elapsed_macro = 0.0

        while elapsed_macro < dt_s - 1e-6:
            # Determine adaptive sub-step dt_sub based on CFL condition
            max_depth = float(np.max(h))
            if max_depth > min_h:
                c = np.sqrt(g * max_depth)
                dt_cfl = substep_cfl * (dx / max(c, 0.1))
                dt_sub = min(dt_s - elapsed_macro, max(1.0, min(5.0, dt_cfl)))
            else:
                dt_sub = min(dt_s - elapsed_macro, 5.0)

            eta = h + dem

            # ----------------------------------------------------
            # 1. Update X-Discharge (East-West interfaces)
            # ----------------------------------------------------
            eta_w = eta[:, :-1]
            eta_e = eta[:, 1:]
            hf_x = np.maximum(0.0, np.maximum(eta_w, eta_e) - z_max_x)

            wet_mask_x = hf_x > min_h
            if np.any(wet_mask_x):
                d_eta_x = (eta_e - eta_w) / dx
                # Friction denominator: 1 + g * dt_sub * n^2 * |q| / hf^(7/3)
                hf_pow_x = hf_x ** (7.0 / 3.0) + 1e-7
                friction_denom_x = 1.0 + g * dt_sub * (manning_n ** 2) * np.abs(qx) / hf_pow_x
                # Local inertial momentum equation
                qx_new = (qx - g * hf_x * dt_sub * d_eta_x) / friction_denom_x
                # Zero out dry interfaces
                qx = np.where(wet_mask_x, qx_new, 0.0)
            else:
                qx.fill(0.0)

            # ----------------------------------------------------
            # 2. Update Y-Discharge (North-South interfaces)
            # ----------------------------------------------------
            eta_n = eta[:-1, :]
            eta_s = eta[1:, :]
            hf_y = np.maximum(0.0, np.maximum(eta_n, eta_s) - z_max_y)

            wet_mask_y = hf_y > min_h
            if np.any(wet_mask_y):
                d_eta_y = (eta_s - eta_n) / dx
                hf_pow_y = hf_y ** (7.0 / 3.0) + 1e-7
                friction_denom_y = 1.0 + g * dt_sub * (manning_n ** 2) * np.abs(qy) / hf_pow_y
                qy_new = (qy - g * hf_y * dt_sub * d_eta_y) / friction_denom_y
                qy = np.where(wet_mask_y, qy_new, 0.0)
            else:
                qy.fill(0.0)

            # ----------------------------------------------------
            # 3. Continuity / Mass update
            # ----------------------------------------------------
            # Net flux into cell = (q_in - q_out)
            # Divergence of qx: shape (rows, cols)
            flux_x = np.zeros((rows, cols), dtype=np.float64)
            flux_x[:, 0] = -qx[:, 0]
            flux_x[:, 1:-1] = qx[:, :-1] - qx[:, 1:]
            flux_x[:, -1] = qx[:, -1]

            # Divergence of qy: shape (rows, cols)
            flux_y = np.zeros((rows, cols), dtype=np.float64)
            flux_y[0, :] = -qy[0, :]
            flux_y[1:-1, :] = qy[:-1, :] - qy[1:, :]
            flux_y[-1, :] = qy[-1, :]

            # Hydrodynamic water increment
            dh_flow = (dt_sub / dx) * (flux_x + flux_y)

            # Source term: Rainfall
            dh_rain = dt_sub * r_rate

            # Sink term: Drainage / Infiltration (bounded by water available)
            h_inter = np.maximum(0.0, h + dh_flow + dh_rain)
            dh_drain = np.minimum(h_inter, dt_sub * drain_rate_mps)
            cum_drain_m3 += float(np.sum(dh_drain)) * (dx * dx)

            # Final depth update enforcing non-negativity
            h = np.maximum(0.0, h_inter - dh_drain)

            elapsed_macro += dt_sub

        cum_drain_m3_series[step_idx + 1] = cum_drain_m3
        # Record macro frame
        depth_frames[step_idx + 1] = np.round(h, 4).astype(np.float32)

        # Approximate velocity: v = sqrt(qx^2 + qy^2) / max(h, min_h)
        # Interpolate fluxes to cell centers
        v_x = np.zeros((rows, cols), dtype=np.float32)
        v_x[:, :-1] += 0.5 * np.abs(qx).astype(np.float32)
        v_x[:, 1:] += 0.5 * np.abs(qx).astype(np.float32)

        v_y = np.zeros((rows, cols), dtype=np.float32)
        v_y[:-1, :] += 0.5 * np.abs(qy).astype(np.float32)
        v_y[1:, :] += 0.5 * np.abs(qy).astype(np.float32)

        h_safe = np.maximum(depth_frames[step_idx + 1], min_h)
        speed = np.sqrt(v_x ** 2 + v_y ** 2) / h_safe
        max_velocity_frames[step_idx + 1] = np.where(
            depth_frames[step_idx + 1] >= WET_THRESHOLD_M, speed, 0.0
        )

    solve_time_s = round(float(time.perf_counter() - t_start), 3)

    return {
        "depth_frames": depth_frames,
        "times_s": times_s,
        "max_velocity_frames": max_velocity_frames,
        "solve_time_s": max(0.001, solve_time_s),
        "cum_drain_m3_series": cum_drain_m3_series,
    }
