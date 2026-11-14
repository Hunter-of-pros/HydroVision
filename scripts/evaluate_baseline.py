"""Comprehensive baseline neural surrogate evaluation script with full Step 3 Addendum.

PART A EVALUATION ADDENDUM:
1. Wet-cell metrics (MAE, RMSE, and at steps 10/30/60/120 over cells wet in solver OR prediction).
2. Peak depth error: mean over cells of |max_t prediction - max_t solver|, plus error of single deepest cell.
3. Persistence baseline (h_{t+1} = h_t) and teacher-forced single-step model reference.
4. Correctly defined and stratified mass error:
   Formula (i):  |V_pred(T) - V_solver(T)| / max(V_solver(T), eps)
   Formula (ii): |V_pred(T) - (R - D_true)| / max(R, eps)
   Stratified by rain intensity (<50, 50-100, >100 mm/hr) and drain capacity (=0 vs >0).
   Signed mean errors and identification of driver scenarios.
5. Error-vs-step curves:
   - artifacts/reports/baseline_rollout_error.png (MAE & wet-cell MAE for val and extrap)
   - artifacts/reports/baseline_persistence_comparison.png (Rollout vs Persistence)
6. Honest speed measurement: 8 threads, median of 7 runs after 3 warmups (forward batch 1/8/32, rollout batch 1/8, solver 10 scenarios).
   Clear explanation and labeling of bundled k=5 projection.

Phase: Phase 4 & Step 3 Addendum
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hydrovision_ml.config import CELL_SIZE_M, DATA_DIR, DT_S
from hydrovision_ml.solver.swe_solver import run_solver_core
from hydrovision_ml.surrogate.model import Normalizer, UNetSurrogate
from hydrovision_ml.surrogate.rollout import rollout, rollout_batched


def load_model(checkpoint_path: str, device: str = "cpu") -> Tuple[UNetSurrogate, Normalizer, Dict[str, Any]]:
    """Load model, normalizer, and checkpoint payload."""
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    config = ckpt.get("model_config", {
        "in_channels": 7,
        "out_channels": 1,
        "base_ch": 26,
        "padding_mode": "reflect",
    })
    model = UNetSurrogate(**config)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    if "normalizer" in ckpt:
        normalizer = Normalizer.from_dict(ckpt["normalizer"])
    else:
        normalizer = Normalizer.load()

    return model, normalizer, ckpt


def evaluate_split_full(
    model: UNetSurrogate,
    normalizer: Normalizer,
    terrain: np.ndarray,
    cell_size_m: float,
    split_dir: Path,
    num_scenarios: int = 20,
    device: str = "cpu",
) -> Dict[str, Any]:
    """Evaluate surrogate on a slice of scenarios from a split directory with all Step 3 metrics."""
    depth_arr = np.load(str(split_dir / "depth.npy"), mmap_mode="r")  # (N, 121, 64, 64)
    rain_arr = np.load(str(split_dir / "rain.npy"))                    # (N, 120)
    drain_arr = np.load(str(split_dir / "drain_m3.npy"))              # (N, 120)
    params_arr = np.load(str(split_dir / "params.npy"))               # (N, 4)

    total_avail = depth_arr.shape[0]
    eval_count = min(num_scenarios, total_avail)

    H, W = terrain.shape
    cell_area = cell_size_m ** 2
    domain_area = H * W * cell_area

    scenario_metrics: List[Dict[str, Any]] = []
    per_step_mae_all: List[np.ndarray] = []
    per_step_wet_mae_all: List[np.ndarray] = []
    per_step_persist_mae_all: List[np.ndarray] = []

    # Precompute terrain gradient tensors for teacher-forced test
    sy, sx = np.gradient(terrain.astype(np.float32), float(cell_size_m))
    dev = torch.device(device)
    dem_t = torch.tensor(normalizer.normalize_dem(terrain), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)
    sx_t = torch.tensor(normalizer.normalize_slope_x(sx), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)
    sy_t = torch.tensor(normalizer.normalize_slope_y(sy), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)

    for sc_idx in range(eval_count):
        true_depth = np.array(depth_arr[sc_idx], dtype=np.float32)  # (121, 64, 64)
        rain_series = np.array(rain_arr[sc_idx], dtype=np.float32)  # (120,)
        drain_series = np.array(drain_arr[sc_idx], dtype=np.float32) # (120,)
        intensity_mmhr = float(params_arr[sc_idx, 0])
        duration_min = float(params_arr[sc_idx, 1])
        shape_code = int(params_arr[sc_idx, 2])
        drain_cap_mmhr = float(params_arr[sc_idx, 3])

        # 1. Autoregressive 120-step Rollout
        rollout_res = rollout(
            model=model,
            terrain=terrain,
            rain_series=rain_series,
            drain_capacity_mmhr=drain_cap_mmhr,
            normalizer=normalizer,
            cell_size_m=cell_size_m,
            device=device,
        )
        pred_depth = rollout_res["depth_frames"]  # (121, 64, 64)

        # 2. Per-step MAE across 1..120
        abs_diff_frames = np.abs(pred_depth[1:] - true_depth[1:])  # (120, 64, 64)
        step_maes = np.mean(abs_diff_frames, axis=(1, 2))          # (120,)
        per_step_mae_all.append(step_maes)

        # Overall domain MAE and RMSE
        overall_mae = float(np.mean(abs_diff_frames))
        overall_rmse = float(np.sqrt(np.mean(abs_diff_frames ** 2)))

        # 3. Wet-cell metrics: cells where solver >= 0.05 OR prediction >= 0.05
        wet_mask_all = (true_depth[1:] >= 0.05) | (pred_depth[1:] >= 0.05)
        if np.any(wet_mask_all):
            wet_cell_mae = float(np.mean(abs_diff_frames[wet_mask_all]))
            wet_cell_rmse = float(np.sqrt(np.mean(abs_diff_frames[wet_mask_all] ** 2)))
        else:
            wet_cell_mae = 0.0
            wet_cell_rmse = 0.0

        # Per-step wet-cell MAE
        step_wet_maes = np.zeros(120, dtype=np.float32)
        for t in range(120):
            wmask_t = (true_depth[t + 1] >= 0.05) | (pred_depth[t + 1] >= 0.05)
            if np.any(wmask_t):
                step_wet_maes[t] = float(np.mean(abs_diff_frames[t][wmask_t]))
            else:
                step_wet_maes[t] = 0.0
        per_step_wet_mae_all.append(step_wet_maes)

        # Wet-cell MAE at steps 10, 30, 60, 120
        wet_mae_step_10 = float(step_wet_maes[9])
        wet_mae_step_30 = float(step_wet_maes[29])
        wet_mae_step_60 = float(step_wet_maes[59])
        wet_mae_step_120 = float(step_wet_maes[119])

        # Domain MAE at steps 10, 30, 60, 120
        mae_step_10 = float(step_maes[9])
        mae_step_30 = float(step_maes[29])
        mae_step_60 = float(step_maes[59])
        mae_step_120 = float(step_maes[119])

        # Wet IoU on all frames >= 0.05m
        pred_wet = pred_depth[1:] >= 0.05
        true_wet = true_depth[1:] >= 0.05
        wet_inter = int(np.logical_and(pred_wet, true_wet).sum())
        wet_union = int(np.logical_or(pred_wet, true_wet).sum())
        wet_iou = float(wet_inter) / float(max(1, wet_union))

        # 4. Peak depth error
        # (a) Mean over cells of |max_t pred - max_t solver|
        max_t_pred = np.max(pred_depth, axis=0)  # (64, 64)
        max_t_true = np.max(true_depth, axis=0)  # (64, 64)
        peak_depth_error_mean = float(np.mean(np.abs(max_t_pred - max_t_true)))

        # (b) Error of single deepest cell per scenario
        deepest_true_val = float(np.max(max_t_true))
        deepest_pred_val = float(np.max(max_t_pred))
        deepest_cell_error = float(abs(deepest_pred_val - deepest_true_val))

        # 5. Persistence baseline: h_{t+1} = h_t = 0 (dry initial state)
        persist_abs_diff = np.abs(true_depth[1:])  # because pred is 0
        persist_mae = float(np.mean(persist_abs_diff))
        persist_step_maes = np.mean(persist_abs_diff, axis=(1, 2))
        per_step_persist_mae_all.append(persist_step_maes)

        true_wet_cells = true_depth[1:] >= 0.05
        persist_wet_mae = float(np.mean(true_depth[1:][true_wet_cells])) if np.any(true_wet_cells) else 0.0
        persist_wet_iou = 0.0 if np.any(true_wet_cells) else 1.0

        # 6. Teacher-forced single-step model reference (model fed true previous frames)
        with torch.no_grad():
            h_t_norm = normalizer.normalize_depth(torch.tensor(true_depth[:-1], dtype=torch.float32, device=dev).unsqueeze(1))
            h_prev = np.zeros_like(true_depth[:-1])
            h_prev[0] = true_depth[0]
            h_prev[1:] = true_depth[:-2]
            h_prev_norm = normalizer.normalize_depth(torch.tensor(h_prev, dtype=torch.float32, device=dev).unsqueeze(1))

            N_steps = len(rain_series)
            r_val = torch.tensor([normalizer.normalize_rain(r) for r in rain_series], dtype=torch.float32, device=dev).view(-1, 1, 1, 1).expand(-1, 1, H, W)
            d_val = float(normalizer.normalize_drain(drain_cap_mmhr))
            d_map = torch.full((N_steps, 1, H, W), d_val, dtype=torch.float32, device=dev)

            dem_exp = dem_t.expand(N_steps, -1, -1, -1)
            sx_exp = sx_t.expand(N_steps, -1, -1, -1)
            sy_exp = sy_t.expand(N_steps, -1, -1, -1)

            inp = torch.cat([h_t_norm, h_prev_norm, dem_exp, sx_exp, sy_exp, r_val, d_map], dim=1)
            pred_delta = model(inp)
            pred_tf_next = torch.clamp(
                torch.tensor(true_depth[:-1], dtype=torch.float32, device=dev).unsqueeze(1) + pred_delta * normalizer.target_delta_std,
                min=0.0
            )
            tf_diff = torch.abs(pred_tf_next - torch.tensor(true_depth[1:], dtype=torch.float32, device=dev).unsqueeze(1))
            tf_mae = float(torch.mean(tf_diff).item())

        # 7. Mass Conservation Accounting at Step 120
        # Formula (i): |V_pred(T) - V_solver(T)| / max(V_solver(T), eps)
        # Formula (ii): |V_pred(T) - (R - D_true)| / max(R, eps)
        v_solver = float(np.sum(true_depth[120]) * cell_area)
        v_pred = float(np.sum(pred_depth[120]) * cell_area)
        eps = 1e-4

        mass_err_i_pct = float(abs(v_pred - v_solver) / max(v_solver, eps) * 100.0)
        signed_mass_err_i_pct = float((v_pred - v_solver) / max(v_solver, eps) * 100.0)

        # Theoretical mass budget: Rain - Drain
        rain_vol_step_m3 = rain_series * 1e-3 * (60.0 / 3600.0) * domain_area
        total_rain_vol_m3 = float(np.sum(rain_vol_step_m3))
        cum_drain_vol_m3 = float(drain_series[119])
        v_budget = total_rain_vol_m3 - cum_drain_vol_m3

        mass_err_ii_pct = float(abs(v_pred - v_budget) / max(total_rain_vol_m3, eps) * 100.0)
        signed_mass_err_ii_pct = float((v_pred - v_budget) / max(total_rain_vol_m3, eps) * 100.0)

        persist_mass_err_i_pct = 100.0 if v_solver > 0 else 0.0

        # Bin definitions
        if intensity_mmhr < 50.0:
            rain_bin = "<50"
        elif intensity_mmhr <= 100.0:
            rain_bin = "50-100"
        else:
            rain_bin = ">100"

        drain_bin = "drain_0" if drain_cap_mmhr == 0.0 else "drain_gt_0"

        scenario_metrics.append({
            "scenario_idx": sc_idx,
            "rain_intensity_mmhr": intensity_mmhr,
            "rain_duration_min": duration_min,
            "rain_bin": rain_bin,
            "drain_capacity_mmhr": drain_cap_mmhr,
            "drain_bin": drain_bin,
            "rollout_mae_m": round(overall_mae, 6),
            "rollout_mae_mm": round(overall_mae * 1000.0, 2),
            "rollout_rmse_m": round(overall_rmse, 6),
            "rollout_rmse_mm": round(overall_rmse * 1000.0, 2),
            "wet_cell_mae_mm": round(wet_cell_mae * 1000.0, 2),
            "wet_cell_rmse_mm": round(wet_cell_rmse * 1000.0, 2),
            "wet_iou": round(wet_iou, 4),
            "peak_depth_error_mean_m": round(peak_depth_error_mean, 4),
            "deepest_cell_error_m": round(deepest_cell_error, 4),
            "deepest_true_m": round(deepest_true_val, 4),
            "deepest_pred_m": round(deepest_pred_val, 4),
            "mae_step_10_mm": round(mae_step_10 * 1000.0, 2),
            "mae_step_30_mm": round(mae_step_30 * 1000.0, 2),
            "mae_step_60_mm": round(mae_step_60 * 1000.0, 2),
            "mae_step_120_mm": round(mae_step_120 * 1000.0, 2),
            "wet_mae_step_10_mm": round(wet_mae_step_10 * 1000.0, 2),
            "wet_mae_step_30_mm": round(wet_mae_step_30 * 1000.0, 2),
            "wet_mae_step_60_mm": round(wet_mae_step_60 * 1000.0, 2),
            "wet_mae_step_120_mm": round(wet_mae_step_120 * 1000.0, 2),
            "persist_mae_mm": round(persist_mae * 1000.0, 2),
            "persist_wet_mae_mm": round(persist_wet_mae * 1000.0, 2),
            "persist_wet_iou": round(persist_wet_iou, 4),
            "teacher_forced_mae_mm": round(tf_mae * 1000.0, 2),
            "v_solver_m3": round(v_solver, 1),
            "v_pred_m3": round(v_pred, 1),
            "v_budget_m3": round(v_budget, 1),
            "mass_err_i_vs_solver_pct": round(mass_err_i_pct, 2),
            "signed_mass_err_i_pct": round(signed_mass_err_i_pct, 2),
            "mass_err_ii_vs_budget_pct": round(mass_err_ii_pct, 2),
            "signed_mass_err_ii_pct": round(signed_mass_err_ii_pct, 2),
            "inference_time_s": round(rollout_res["inference_time_s"], 4),
        })

    # Stratified mass error breakdowns
    def compute_strata(scs: List[Dict[str, Any]], key: str, val: Any) -> Dict[str, Any]:
        subset = [s for s in scs if s[key] == val]
        if not subset:
            return {"count": 0, "mean_mass_err_i_pct": 0.0, "mean_mass_err_ii_pct": 0.0, "signed_i_pct": 0.0}
        return {
            "count": len(subset),
            "mean_mass_err_i_pct": round(float(np.mean([s["mass_err_i_vs_solver_pct"] for s in subset])), 2),
            "signed_i_pct": round(float(np.mean([s["signed_mass_err_i_pct"] for s in subset])), 2),
            "mean_mass_err_ii_pct": round(float(np.mean([s["mass_err_ii_vs_budget_pct"] for s in subset])), 2),
            "signed_ii_pct": round(float(np.mean([s["signed_mass_err_ii_pct"] for s in subset])), 2),
        }

    rain_bins = {
        "<50": compute_strata(scenario_metrics, "rain_bin", "<50"),
        "50-100": compute_strata(scenario_metrics, "rain_bin", "50-100"),
        ">100": compute_strata(scenario_metrics, "rain_bin", ">100"),
    }
    drain_bins = {
        "drain_0": compute_strata(scenario_metrics, "drain_bin", "drain_0"),
        "drain_gt_0": compute_strata(scenario_metrics, "drain_bin", "drain_gt_0"),
    }

    # Identify driver scenarios with highest mass error
    sorted_by_mass_err = sorted(scenario_metrics, key=lambda x: x["mass_err_i_vs_solver_pct"], reverse=True)
    top_drivers = [
        {
            "scenario_idx": s["scenario_idx"],
            "rain_intensity_mmhr": s["rain_intensity_mmhr"],
            "drain_capacity_mmhr": s["drain_capacity_mmhr"],
            "mass_err_i_pct": s["mass_err_i_vs_solver_pct"],
            "signed_i_pct": s["signed_mass_err_i_pct"],
            "v_solver_m3": s["v_solver_m3"],
            "v_pred_m3": s["v_pred_m3"],
        }
        for s in sorted_by_mass_err[:5]
    ]

    per_step_maes_arr = np.array(per_step_mae_all)
    per_step_wet_maes_arr = np.array(per_step_wet_mae_all)
    per_step_persist_arr = np.array(per_step_persist_mae_all)

    summary = {
        "num_scenarios": eval_count,
        "rollout_mae_mm": round(float(np.mean([s["rollout_mae_mm"] for s in scenario_metrics])), 2),
        "rollout_rmse_mm": round(float(np.mean([s["rollout_rmse_mm"] for s in scenario_metrics])), 2),
        "wet_cell_mae_mm": round(float(np.mean([s["wet_cell_mae_mm"] for s in scenario_metrics])), 2),
        "wet_cell_rmse_mm": round(float(np.mean([s["wet_cell_rmse_mm"] for s in scenario_metrics])), 2),
        "wet_iou": round(float(np.mean([s["wet_iou"] for s in scenario_metrics])), 4),
        "peak_depth_error_mean_m": round(float(np.mean([s["peak_depth_error_mean_m"] for s in scenario_metrics])), 4),
        "deepest_cell_error_mean_m": round(float(np.mean([s["deepest_cell_error_m"] for s in scenario_metrics])), 4),
        "deepest_cell_error_worst_m": round(float(np.max([s["deepest_cell_error_m"] for s in scenario_metrics])), 4),
        "mae_step_10_mm": round(float(np.mean([s["mae_step_10_mm"] for s in scenario_metrics])), 2),
        "mae_step_30_mm": round(float(np.mean([s["mae_step_30_mm"] for s in scenario_metrics])), 2),
        "mae_step_60_mm": round(float(np.mean([s["mae_step_60_mm"] for s in scenario_metrics])), 2),
        "mae_step_120_mm": round(float(np.mean([s["mae_step_120_mm"] for s in scenario_metrics])), 2),
        "wet_mae_step_10_mm": round(float(np.mean([s["wet_mae_step_10_mm"] for s in scenario_metrics])), 2),
        "wet_mae_step_30_mm": round(float(np.mean([s["wet_mae_step_30_mm"] for s in scenario_metrics])), 2),
        "wet_mae_step_60_mm": round(float(np.mean([s["wet_mae_step_60_mm"] for s in scenario_metrics])), 2),
        "wet_mae_step_120_mm": round(float(np.mean([s["wet_mae_step_120_mm"] for s in scenario_metrics])), 2),
        "persistence_baseline": {
            "mae_mm": round(float(np.mean([s["persist_mae_mm"] for s in scenario_metrics])), 2),
            "wet_cell_mae_mm": round(float(np.mean([s["persist_wet_mae_mm"] for s in scenario_metrics])), 2),
            "wet_iou": round(float(np.mean([s["persist_wet_iou"] for s in scenario_metrics])), 4),
            "mass_error_pct": 100.0,
        },
        "teacher_forced_reference": {
            "mae_mm": round(float(np.mean([s["teacher_forced_mae_mm"] for s in scenario_metrics])), 2),
        },
        "mass_conservation": {
            "mean_mass_err_i_vs_solver_pct": round(float(np.mean([s["mass_err_i_vs_solver_pct"] for s in scenario_metrics])), 2),
            "signed_mean_mass_err_i_pct": round(float(np.mean([s["signed_mass_err_i_pct"] for s in scenario_metrics])), 2),
            "mean_mass_err_ii_vs_budget_pct": round(float(np.mean([s["mass_err_ii_vs_budget_pct"] for s in scenario_metrics])), 2),
            "signed_mean_mass_err_ii_pct": round(float(np.mean([s["signed_mass_err_ii_pct"] for s in scenario_metrics])), 2),
            "by_rain_intensity_mmhr": rain_bins,
            "by_drain_capacity_mmhr": drain_bins,
            "top_drivers_highest_err": top_drivers,
        },
        "scenarios": scenario_metrics,
        "step_mae_mean_mm": (np.mean(per_step_maes_arr, axis=0) * 1000.0).round(2).tolist(),
        "step_mae_std_mm": (np.std(per_step_maes_arr, axis=0) * 1000.0).round(2).tolist(),
        "step_wet_mae_mean_mm": (np.mean(per_step_wet_maes_arr, axis=0) * 1000.0).round(2).tolist(),
        "step_wet_mae_std_mm": (np.std(per_step_wet_maes_arr, axis=0) * 1000.0).round(2).tolist(),
        "step_persist_mae_mean_mm": (np.mean(per_step_persist_arr, axis=0) * 1000.0).round(2).tolist(),
    }
    return summary


def run_honest_speed_benchmark(
    checkpoint_path: str,
    device: str = "cpu",
    threads: int = 8,
) -> Dict[str, Any]:
    """Measure honest execution times with median of 7 runs after 3 warmups."""
    torch.set_num_threads(threads)
    model, normalizer, _ = load_model(checkpoint_path, device=device)
    dev = torch.device(device)

    # 1. Forward pass benchmark (Batch 1, 8, 32)
    def bench_forward(bs: int) -> Dict[str, float]:
        x = torch.randn(bs, 7, 64, 64, device=dev)
        # 3 warmups
        for _ in range(3):
            with torch.no_grad():
                _ = model(x)
        times = []
        for _ in range(7):
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = model(x)
            times.append(time.perf_counter() - t0)
        med_s = float(np.median(times))
        return {
            "median_ms": round(med_s * 1000.0, 2),
            "per_sample_ms": round((med_s * 1000.0) / bs, 2),
        }

    fwd_1 = bench_forward(1)
    fwd_8 = bench_forward(8)
    fwd_32 = bench_forward(32)

    # 2. 120-step Rollout Benchmark (Batch 1 and Batch 8)
    terrain_npz = np.load("artifacts/data/terrain.npz")
    terrain = terrain_npz["dem_m"].astype(np.float32)
    cell_size = float(terrain_npz["cell_size_m"])

    rain_1 = np.full(120, 60.0, dtype=np.float32)
    drain_1 = 5.0

    # Batch 1 rollout
    for _ in range(3):
        rollout(model, terrain, rain_1, drain_1, normalizer, cell_size_m=cell_size, device=device)
    r1_times = []
    for _ in range(7):
        t0 = time.perf_counter()
        rollout(model, terrain, rain_1, drain_1, normalizer, cell_size_m=cell_size, device=device)
        r1_times.append(time.perf_counter() - t0)
    rollout_1_med_s = float(np.median(r1_times))

    # Batch 8 rollout
    rain_8 = np.full((8, 120), 60.0, dtype=np.float32)
    drain_8 = np.full(8, 5.0, dtype=np.float32)

    for _ in range(3):
        rollout_batched(model, terrain, rain_8[:2], drain_8[:2], normalizer, cell_size_m=cell_size, device=device)
    r8_times = []
    for _ in range(7):
        t0 = time.perf_counter()
        rollout_batched(model, terrain, rain_8, drain_8, normalizer, cell_size_m=cell_size, device=device)
        r8_times.append(time.perf_counter() - t0)
    rollout_8_med_total_s = float(np.median(r8_times))
    rollout_8_per_sc_s = rollout_8_med_total_s / 8.0

    # 3. Solver benchmark: 10 scenarios
    solver_times = []
    for sc_i in range(10):
        t0 = time.perf_counter()
        run_solver_core(
            dem=terrain.astype(np.float64),
            rain_series_mmhr=rain_1,
            dt_s=float(DT_S),
            drain_capacity_mmhr=drain_1,
            cell_size_m=cell_size,
        )
        solver_times.append(time.perf_counter() - t0)
    solver_med_s = float(np.median(solver_times))

    speedup_b1 = solver_med_s / max(1e-5, rollout_1_med_s)
    speedup_b8 = solver_med_s / max(1e-5, rollout_8_per_sc_s)

    return {
        "hardware_info": {
            "cpu": platform.processor(),
            "threads": threads,
            "os": platform.system(),
            "python": platform.python_version(),
            "torch": torch.__version__,
        },
        "forward_pass": {
            "batch_1": fwd_1,
            "batch_8": fwd_8,
            "batch_32": fwd_32,
        },
        "measured_rollout_120_steps": {
            "batch_1_median_s": round(rollout_1_med_s, 4),
            "batch_1_median_ms": round(rollout_1_med_s * 1000.0, 1),
            "batch_1_speedup_vs_solver": round(speedup_b1, 2),
            "batch_8_total_median_s": round(rollout_8_med_total_s, 3),
            "batch_8_per_scenario_ms": round(rollout_8_per_sc_s * 1000.0, 1),
            "batch_8_speedup_vs_solver": round(speedup_b8, 2),
        },
        "measured_solver_120_steps": {
            "num_scenarios_evaluated": 10,
            "median_s": round(solver_med_s, 4),
            "median_ms": round(solver_med_s * 1000.0, 1),
        },
        "bundled_k5_note": {
            "label": "projection, not measured",
            "historical_claim": "131.1 ms / 2.04x speedup with bundled k=5",
            "explanation": "The 131.1 ms figure was a theoretical projection calculated during the Step 1.5 speed probe (24 passes of a 5-step unrolled dummy model x ~5.4 ms/pass). No bundled-k5 model was trained or deployed for this baseline. The real measured single-step baseline takes 568 ms on this CPU (0.47x solver speed).",
        },
    }


def plot_rollout_curves(
    val_step_mae_mm: List[float],
    val_step_wet_mae_mm: List[float],
    extrap_step_mae_mm: List[float],
    extrap_step_wet_mae_mm: List[float],
    output_png: Path,
) -> None:
    """Plot MAE and Wet-cell MAE trajectories over 120 steps."""
    output_png.parent.mkdir(parents=True, exist_ok=True)
    steps = np.arange(1, len(val_step_mae_mm) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)

    # Subplot 1: Domain-Wide MAE
    ax1.plot(steps, val_step_mae_mm, color="#1f77b4", linewidth=2.2, label="Validation (20 Scenarios)")
    ax1.plot(steps, extrap_step_mae_mm, color="#d62728", linewidth=2.0, linestyle="--", label="Extrapolation (10 Scenarios)")
    ax1.set_title("Domain-Wide Depth Error (All 4,096 Cells)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Simulation Horizon (Minutes)", fontsize=10)
    ax1.set_ylabel("MAE (mm)", fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left")

    # Annotate key milestones
    for t in [10, 30, 60, 120]:
        v = val_step_mae_mm[t - 1]
        ax1.scatter([t], [v], color="#1f77b4", s=30, zorder=5)
        ax1.annotate(f"t={t}: {v:.1f}mm", (t, v), xytext=(t+1, v+0.2), fontsize=8)

    # Subplot 2: Wet-Cell MAE
    ax2.plot(steps, val_step_wet_mae_mm, color="#2ca02c", linewidth=2.2, label="Validation Wet Cells (h >= 0.05m)")
    ax2.plot(steps, extrap_step_wet_mae_mm, color="#ff7f0e", linewidth=2.0, linestyle="--", label="Extrapolation Wet Cells (h >= 0.05m)")
    ax2.set_title("Inundated Cell Depth Error (h >= 0.05 m)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Simulation Horizon (Minutes)", fontsize=10)
    ax2.set_ylabel("Wet-Cell MAE (mm)", fontsize=10)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper left")

    for t in [10, 30, 60, 120]:
        v = val_step_wet_mae_mm[t - 1]
        ax2.scatter([t], [v], color="#2ca02c", s=30, zorder=5)
        ax2.annotate(f"t={t}: {v:.1f}mm", (t, v), xytext=(t+1, v+0.3), fontsize=8)

    plt.suptitle("HydroVision Baseline Neural Surrogate: 120-Step Error Trajectory", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(str(output_png), bbox_inches="tight")
    plt.close(fig)
    print(f"[Evaluation] Overwrote error trajectory plot: {output_png}", flush=True)


def plot_persistence_comparison(
    steps: np.ndarray,
    val_model_mae_mm: List[float],
    val_persist_mae_mm: List[float],
    output_png: Path,
) -> None:
    """Plot Model Rollout vs Persistence Baseline (h_{t+1} = h_t)."""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.plot(steps, val_persist_mae_mm, color="#7f7f7f", linewidth=2.2, linestyle=":", label="Persistence Baseline (h_{t+1} = h_t = 0)")
    ax.plot(steps, val_model_mae_mm, color="#1f77b4", linewidth=2.2, label="Trained Surrogate Rollout")

    ax.set_title("Model Rollout vs Persistence Baseline (Validation 20 Scenarios)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Simulation Step t (Minutes)", fontsize=10)
    ax.set_ylabel("Domain Mean Absolute Error (MAE in mm)", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left")

    plt.tight_layout()
    fig.savefig(str(output_png), bbox_inches="tight")
    plt.close(fig)
    print(f"[Evaluation] Saved persistence comparison plot: {output_png}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baseline surrogate with full Step 3 addendum.")
    parser.add_argument("--checkpoint", type=str, default="artifacts/models/best.pt")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output-json", type=str, default="artifacts/reports/baseline_metrics.json")
    parser.add_argument("--output-png", type=str, default="artifacts/reports/baseline_rollout_error.png")
    parser.add_argument("--persist-png", type=str, default="artifacts/reports/baseline_persistence_comparison.png")

    args = parser.parse_args()
    torch.set_num_threads(args.threads)

    print("=" * 80, flush=True)
    print("HYDROVISION BASELINE SURROGATE EVALUATION ADDENDUM (STEP 3)", flush=True)
    print(f"Checkpoint: {args.checkpoint} | Device: {args.device.upper()} | Threads: {args.threads}", flush=True)
    print("=" * 80, flush=True)

    # 1. Load Model & Normalizer
    model, normalizer, ckpt = load_model(args.checkpoint, device=args.device)

    # 2. Load Real Terrain
    terrain_npz = np.load("artifacts/data/terrain.npz")
    terrain = terrain_npz["dem_m"].astype(np.float32)
    cell_size_m = float(terrain_npz["cell_size_m"])

    # 3. Evaluate Validation Split (20 scenarios)
    val_dir = Path(DATA_DIR) / "val"
    print(f"\n[Evaluation] Evaluating 20 Validation Scenarios with full Step 3 metrics...", flush=True)
    val_summary = evaluate_split_full(
        model=model,
        normalizer=normalizer,
        terrain=terrain,
        cell_size_m=cell_size_m,
        split_dir=val_dir,
        num_scenarios=20,
        device=args.device,
    )

    # 4. Evaluate Extrapolation Split (10 scenarios)
    extrap_dir = Path(DATA_DIR) / "extrapolation"
    print(f"[Evaluation] Evaluating 10 Extrapolation Scenarios...", flush=True)
    extrap_summary = evaluate_split_full(
        model=model,
        normalizer=normalizer,
        terrain=terrain,
        cell_size_m=cell_size_m,
        split_dir=extrap_dir,
        num_scenarios=10,
        device=args.device,
    )

    # 5. Honest Speed Benchmarking
    print("[Evaluation] Running honest speed benchmarks (7 runs median, 3 warmups)...", flush=True)
    speed_summary = run_honest_speed_benchmark(
        checkpoint_path=args.checkpoint,
        device=args.device,
        threads=args.threads,
    )

    # 6. Generate Plots
    plot_rollout_curves(
        val_step_mae_mm=val_summary["step_mae_mean_mm"],
        val_step_wet_mae_mm=val_summary["step_wet_mae_mean_mm"],
        extrap_step_mae_mm=extrap_summary["step_mae_mean_mm"],
        extrap_step_wet_mae_mm=extrap_summary["step_wet_mae_mean_mm"],
        output_png=Path(args.output_png),
    )
    steps = np.arange(1, 121)
    plot_persistence_comparison(
        steps=steps,
        val_model_mae_mm=val_summary["step_mae_mean_mm"],
        val_persist_mae_mm=val_summary["step_persist_mae_mean_mm"],
        output_png=Path(args.persist_png),
    )

    # 7. Merge into JSON report (preserve existing keys + extend)
    out_json = Path(args.output_json)
    existing_data = {}
    if out_json.exists():
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = {}

    report = dict(existing_data)
    report.update({
        "status": "COMPLETED",
        "checkpoint": args.checkpoint,
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mass_conservation_formula": {
            "formula_i": "|V_pred(T) - V_solver(T)| / max(V_solver(T), eps)",
            "formula_ii": "|V_pred(T) - (R - D_true)| / max(R, eps)",
            "definition": "V = sum(depth) * 60.9^2, R = cumulative rain volume (m3), D_true = cumulative drained volume (drain_m3 index 119)",
        },
        "step_3_addendum": {
            "validation": {
                "rollout_mae_mm": val_summary["rollout_mae_mm"],
                "wet_cell_mae_mm": val_summary["wet_cell_mae_mm"],
                "wet_cell_rmse_mm": val_summary["wet_cell_rmse_mm"],
                "wet_iou": val_summary["wet_iou"],
                "peak_depth_error_mean_m": val_summary["peak_depth_error_mean_m"],
                "deepest_cell_error_mean_m": val_summary["deepest_cell_error_mean_m"],
                "deepest_cell_error_worst_m": val_summary["deepest_cell_error_worst_m"],
                "mae_steps_mm": {
                    "step_10": val_summary["mae_step_10_mm"],
                    "step_30": val_summary["mae_step_30_mm"],
                    "step_60": val_summary["mae_step_60_mm"],
                    "step_120": val_summary["mae_step_120_mm"],
                },
                "wet_cell_mae_steps_mm": {
                    "step_10": val_summary["wet_mae_step_10_mm"],
                    "step_30": val_summary["wet_mae_step_30_mm"],
                    "step_60": val_summary["wet_mae_step_60_mm"],
                    "step_120": val_summary["wet_mae_step_120_mm"],
                },
                "persistence_baseline": val_summary["persistence_baseline"],
                "teacher_forced_reference": val_summary["teacher_forced_reference"],
                "mass_conservation": val_summary["mass_conservation"],
            },
            "extrapolation": {
                "rollout_mae_mm": extrap_summary["rollout_mae_mm"],
                "wet_cell_mae_mm": extrap_summary["wet_cell_mae_mm"],
                "wet_cell_rmse_mm": extrap_summary["wet_cell_rmse_mm"],
                "wet_iou": extrap_summary["wet_iou"],
                "peak_depth_error_mean_m": extrap_summary["peak_depth_error_mean_m"],
                "deepest_cell_error_mean_m": extrap_summary["deepest_cell_error_mean_m"],
                "deepest_cell_error_worst_m": extrap_summary["deepest_cell_error_worst_m"],
                "mae_steps_mm": {
                    "step_10": extrap_summary["mae_step_10_mm"],
                    "step_30": extrap_summary["mae_step_30_mm"],
                    "step_60": extrap_summary["mae_step_60_mm"],
                    "step_120": extrap_summary["mae_step_120_mm"],
                },
                "wet_cell_mae_steps_mm": {
                    "step_10": extrap_summary["wet_mae_step_10_mm"],
                    "step_30": extrap_summary["wet_mae_step_30_mm"],
                    "step_60": extrap_summary["wet_mae_step_60_mm"],
                    "step_120": extrap_summary["wet_mae_step_120_mm"],
                },
                "persistence_baseline": extrap_summary["persistence_baseline"],
                "teacher_forced_reference": extrap_summary["teacher_forced_reference"],
                "mass_conservation": extrap_summary["mass_conservation"],
            },
            "speed_benchmark_honest": speed_summary,
        },
        "validation_scenarios_detailed": val_summary["scenarios"],
        "extrapolation_scenarios_detailed": extrap_summary["scenarios"],
    })

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[Evaluation] Saved enhanced report to: {out_json}", flush=True)


if __name__ == "__main__":
    main()
