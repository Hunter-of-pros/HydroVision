"""Autoregressive multi-step rollout module for neural surrogate inference.

Supports single-scenario and batched 120-step rollouts from zero initial depth.
Guarantees non-negative depths (clamped to 0.0) and dry initial state at frame 0.

Phase: Phase 4 (Baseline Surrogate)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

import numpy as np
import torch
import torch.nn as nn

from hydrovision_ml.surrogate.model import Normalizer, UNetSurrogate


@torch.no_grad()
def rollout(
    model: nn.Module,
    terrain: np.ndarray,
    rain_series: Union[List[float], np.ndarray],
    drain_capacity_mmhr: float = 0.0,
    normalizer: Optional[Normalizer] = None,
    initial_depth: Optional[np.ndarray] = None,
    cell_size_m: float = 60.9,
    horizon_steps: int = 120,
    device: str = "cpu",
) -> Dict[str, Any]:
    """Execute autoregressive 120-step neural surrogate rollout.

    Parameters
    ----------
    model : nn.Module
        Trained UNetSurrogate instance.
    terrain : np.ndarray
        Static elevation grid (H, W).
    rain_series : list[float] or np.ndarray
        Precipitation intensity per macro step [mm/hr] (length = horizon_steps).
    drain_capacity_mmhr : float
        Uniform drain capacity sink [mm/hr].
    normalizer : Normalizer, optional
        Pre-fitted Normalizer instance. If None, loaded from artifacts/models/normalizer.json.
    initial_depth : np.ndarray, optional
        Initial depth grid at t=0 (H, W). Defaults to all zeros.
    cell_size_m : float
        Grid cell size in meters (default 60.9 m).
    horizon_steps : int
        Simulation horizon steps (default: 120).
    device : str
        Compute device ('cpu' or 'cuda').

    Returns
    -------
    dict
        - 'depth_frames': np.ndarray of shape (horizon_steps + 1, H, W) in float32.
        - 'inference_time_s': float wall-clock runtime in seconds.
    """
    t_start = time.perf_counter()
    model.eval()

    if normalizer is None:
        normalizer = Normalizer.load()

    dev = torch.device(device)
    model.to(dev)

    H, W = terrain.shape
    num_frames = horizon_steps + 1

    # Precompute normalized static terrain and slope fields
    sy, sx = np.gradient(terrain.astype(np.float32), float(cell_size_m))
    dem_norm_t = torch.tensor(normalizer.normalize_dem(terrain), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)  # (1, 1, H, W)
    sx_norm_t = torch.tensor(normalizer.normalize_slope_x(sx), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)    # (1, 1, H, W)
    sy_norm_t = torch.tensor(normalizer.normalize_slope_y(sy), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)    # (1, 1, H, W)
    drain_norm_val = float(normalizer.normalize_drain(drain_capacity_mmhr))
    drain_map = torch.full((1, 1, H, W), drain_norm_val, dtype=torch.float32, device=dev)

    # Initialize states
    if initial_depth is not None:
        h_0 = torch.tensor(initial_depth, dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)
    else:
        h_0 = torch.zeros((1, 1, H, W), dtype=torch.float32, device=dev)

    h_t = h_0.clone()
    h_prev = h_0.clone()

    depth_frames = np.zeros((num_frames, H, W), dtype=np.float32)
    depth_frames[0] = h_0.squeeze().cpu().numpy()

    rain_arr = np.asarray(rain_series, dtype=np.float32)

    for step in range(horizon_steps):
        r_val = float(normalizer.normalize_rain(rain_arr[step]))
        rain_map = torch.full((1, 1, H, W), r_val, dtype=torch.float32, device=dev)

        # 7-channel input: [h_t_norm, h_prev_norm, dem, slope_x, slope_y, rain, drain]
        h_t_norm = normalizer.normalize_depth(h_t)
        h_prev_norm = normalizer.normalize_depth(h_prev)

        inp = torch.cat([h_t_norm, h_prev_norm, dem_norm_t, sx_norm_t, sy_norm_t, rain_map, drain_map], dim=1)

        # Autoregressive forward step
        delta_norm = model(inp)
        delta_m = delta_norm * normalizer.target_delta_std

        # Advance state with strict physical non-negativity constraint
        h_next = torch.clamp(h_t + delta_m, min=0.0)

        depth_frames[step + 1] = h_next.squeeze().cpu().numpy()

        # Update previous and current states
        h_prev = h_t
        h_t = h_next

    inference_time = float(time.perf_counter() - t_start)
    return {
        "depth_frames": depth_frames,
        "inference_time_s": inference_time,
    }


@torch.no_grad()
def rollout_batched(
    model: nn.Module,
    terrain: np.ndarray,
    rain_batch: np.ndarray,
    drain_capacities: np.ndarray,
    normalizer: Optional[Normalizer] = None,
    cell_size_m: float = 60.9,
    horizon_steps: int = 120,
    device: str = "cpu",
) -> Dict[str, Any]:
    """Execute batched autoregressive rollout for multiple scenarios concurrently.

    Parameters
    ----------
    model : nn.Module
        Trained surrogate model.
    terrain : np.ndarray
        Static elevation grid (H, W).
    rain_batch : np.ndarray
        Precipitation series of shape (B, horizon_steps) in mm/hr.
    drain_capacities : np.ndarray
        Drain capacities of shape (B,) in mm/hr.
    """
    t_start = time.perf_counter()
    model.eval()

    if normalizer is None:
        normalizer = Normalizer.load()

    dev = torch.device(device)
    model.to(dev)

    B = rain_batch.shape[0]
    H, W = terrain.shape
    num_frames = horizon_steps + 1

    sy, sx = np.gradient(terrain.astype(np.float32), float(cell_size_m))
    dem_t = torch.tensor(normalizer.normalize_dem(terrain), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0).expand(B, 1, H, W)
    sx_t = torch.tensor(normalizer.normalize_slope_x(sx), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0).expand(B, 1, H, W)
    sy_t = torch.tensor(normalizer.normalize_slope_y(sy), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0).expand(B, 1, H, W)

    drain_norms = torch.tensor(
        [normalizer.normalize_drain(d) for d in drain_capacities],
        dtype=torch.float32,
        device=dev,
    ).view(B, 1, 1, 1).expand(B, 1, H, W)

    h_t = torch.zeros((B, 1, H, W), dtype=torch.float32, device=dev)
    h_prev = torch.zeros((B, 1, H, W), dtype=torch.float32, device=dev)

    frames = np.zeros((B, num_frames, H, W), dtype=np.float32)

    for step in range(horizon_steps):
        r_step = rain_batch[:, step]
        r_norms = torch.tensor(
            [normalizer.normalize_rain(r) for r in r_step],
            dtype=torch.float32,
            device=dev,
        ).view(B, 1, 1, 1).expand(B, 1, H, W)

        h_t_norm = normalizer.normalize_depth(h_t)
        h_prev_norm = normalizer.normalize_depth(h_prev)

        inp = torch.cat([h_t_norm, h_prev_norm, dem_t, sx_t, sy_t, r_norms, drain_norms], dim=1)

        delta_norm = model(inp)
        delta_m = delta_norm * normalizer.target_delta_std

        h_next = torch.clamp(h_t + delta_m, min=0.0)
        frames[:, step + 1] = h_next.squeeze(1).cpu().numpy()

        h_prev = h_t
        h_t = h_next

    total_time = float(time.perf_counter() - t_start)
    return {
        "depth_frames": frames,
        "total_time_s": total_time,
        "time_per_scenario_s": total_time / max(1, B),
    }
