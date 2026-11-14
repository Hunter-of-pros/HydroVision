"""Comprehensive baseline neural surrogate evaluation script.

Evaluates trained baseline surrogate (best.pt) on:
- 20 validation scenarios (seen distribution: rain 20-150 mm/hr)
- 10 extrapolation scenarios (unseen distribution: rain 150-180 mm/hr)

Metrics:
- Single-step MAE (m & mm)
- 120-step autoregressive rollout MAE, RMSE, Wet IoU (>= 0.05m)
- Rollout MAE at steps 10, 30, 60, 120
- Mass conservation error (% vs solver final volume, % vs rain - drain budget)
- Wall-clock rollout latency (Batch 1 and batched) vs SWE solver baseline (0.267 s)
- Error trajectory plot saved to artifacts/reports/baseline_rollout_error.png
- Comprehensive JSON saved to artifacts/reports/baseline_metrics.json

Phase: Phase 4 (Baseline Surrogate Evaluation)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
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

from hydrovision_ml.config import DATA_DIR
from hydrovision_ml.surrogate.model import Normalizer, UNetSurrogate
from hydrovision_ml.surrogate.rollout import rollout, rollout_batched

SOLVER_BASELINE_TIME_S = 0.267  # Measured SWE solver reference time for 120 steps


def load_model(checkpoint_path: str, device: str = "cpu") -> Tuple[UNetSurrogate, Normalizer]:
    """Load model and normalizer from checkpoint."""
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

    return model, normalizer


def evaluate_split(
    model: UNetSurrogate,
    normalizer: Normalizer,
    terrain: np.ndarray,
    cell_size_m: float,
    split_dir: Path,
    num_scenarios: int = 20,
    device: str = "cpu",
) -> Dict[str, Any]:
    """Evaluate surrogate on a slice of scenarios from a split directory."""
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
    per_step_mae_all: List[np.ndarray] = []  # shape (eval_count, 120)

    # Precompute terrain gradient tensors for single-step test
    sy, sx = np.gradient(terrain.astype(np.float32), float(cell_size_m))
    dev = torch.device(device)
    dem_t = torch.tensor(normalizer.normalize_dem(terrain), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)
    sx_t = torch.tensor(normalizer.normalize_slope_x(sx), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)
    sy_t = torch.tensor(normalizer.normalize_slope_y(sy), dtype=torch.float32, device=dev).unsqueeze(0).unsqueeze(0)

    for sc_idx in range(eval_count):
        true_depth = np.array(depth_arr[sc_idx], dtype=np.float32)  # (121, 64, 64)
        rain_series = np.array(rain_arr[sc_idx], dtype=np.float32)  # (120,)
        drain_series = np.array(drain_arr[sc_idx], dtype=np.float32) # (120,)
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

        # 3. Aggregated 120-step rollout metrics
        overall_mae = float(np.mean(abs_diff_frames))
        overall_rmse = float(np.sqrt(np.mean(abs_diff_frames ** 2)))

        # Wet IoU on all frames >= 0.05m
        pred_wet = pred_depth[1:] >= 0.05
        true_wet = true_depth[1:] >= 0.05
        wet_inter = int(np.logical_and(pred_wet, true_wet).sum())
        wet_union = int(np.logical_or(pred_wet, true_wet).sum())
        wet_iou = float(wet_inter) / float(max(1, wet_union))

        # Checkpoint step MAEs
        mae_step_10 = float(step_maes[min(9, len(step_maes)-1)])
        mae_step_30 = float(step_maes[min(29, len(step_maes)-1)])
        mae_step_60 = float(step_maes[min(59, len(step_maes)-1)])
        mae_step_120 = float(step_maes[min(119, len(step_maes)-1)])

        # 4. Mass Conservation Accounting at Step 120
        v_solver = float(np.sum(true_depth[120]) * cell_area)
        v_pred = float(np.sum(pred_depth[120]) * cell_area)
        mass_err_vs_solver_pct = float(abs(v_pred - v_solver) / max(1.0, v_solver) * 100.0)

        # Theoretical mass budget (Rain - Drain)
        # rain_series mm/hr applied for 60s per step
        rain_vol_step_m3 = rain_series * 1e-3 * (60.0 / 3600.0) * domain_area
        total_rain_vol_m3 = float(np.sum(rain_vol_step_m3))
        cum_drain_vol_m3 = float(drain_series[119])
        v_expected = total_rain_vol_m3 - cum_drain_vol_m3
        mass_err_vs_budget_pct = float(abs(v_pred - v_expected) / max(1.0, total_rain_vol_m3) * 100.0)

        # 5. Single-step test (teacher forcing)
        with torch.no_grad():
            h_t_norm = normalizer.normalize_depth(torch.tensor(true_depth[:-1], dtype=torch.float32, device=dev).unsqueeze(1))
            # previous depths
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
            pred_step_next = torch.clamp(
                torch.tensor(true_depth[:-1], dtype=torch.float32, device=dev).unsqueeze(1) + pred_delta * normalizer.target_delta_std,
                min=0.0
            )
            single_step_diff = torch.abs(pred_step_next - torch.tensor(true_depth[1:], dtype=torch.float32, device=dev).unsqueeze(1))
            single_step_mae = float(torch.mean(single_step_diff).item())

        scenario_metrics.append({
            "scenario_idx": sc_idx,
            "rain_intensity_mmhr": float(params_arr[sc_idx, 0]),
            "drain_capacity_mmhr": drain_cap_mmhr,
            "single_step_mae_m": round(single_step_mae, 6),
            "single_step_mae_mm": round(single_step_mae * 1000.0, 2),
            "rollout_mae_m": round(overall_mae, 6),
            "rollout_mae_mm": round(overall_mae * 1000.0, 2),
            "rollout_rmse_m": round(overall_rmse, 6),
            "rollout_rmse_mm": round(overall_rmse * 1000.0, 2),
            "wet_iou": round(wet_iou, 4),
            "mae_step_10_mm": round(mae_step_10 * 1000.0, 2),
            "mae_step_30_mm": round(mae_step_30 * 1000.0, 2),
            "mae_step_60_mm": round(mae_step_60 * 1000.0, 2),
            "mae_step_120_mm": round(mae_step_120 * 1000.0, 2),
            "final_volume_solver_m3": round(v_solver, 1),
            "final_volume_pred_m3": round(v_pred, 1),
            "mass_err_vs_solver_pct": round(mass_err_vs_solver_pct, 2),
            "mass_err_vs_budget_pct": round(mass_err_vs_budget_pct, 2),
            "inference_time_s": round(rollout_res["inference_time_s"], 4),
        })

    per_step_maes_arr = np.array(per_step_mae_all)  # (eval_count, 120)
    mean_per_step_mae = np.mean(per_step_maes_arr, axis=0)
    std_per_step_mae = np.std(per_step_maes_arr, axis=0)

    summary = {
        "num_scenarios": eval_count,
        "single_step_mae_mm": round(float(np.mean([s["single_step_mae_mm"] for s in scenario_metrics])), 2),
        "rollout_mae_mm": round(float(np.mean([s["rollout_mae_mm"] for s in scenario_metrics])), 2),
        "rollout_rmse_mm": round(float(np.mean([s["rollout_rmse_mm"] for s in scenario_metrics])), 2),
        "wet_iou": round(float(np.mean([s["wet_iou"] for s in scenario_metrics])), 4),
        "mae_step_10_mm": round(float(np.mean([s["mae_step_10_mm"] for s in scenario_metrics])), 2),
        "mae_step_30_mm": round(float(np.mean([s["mae_step_30_mm"] for s in scenario_metrics])), 2),
        "mae_step_60_mm": round(float(np.mean([s["mae_step_60_mm"] for s in scenario_metrics])), 2),
        "mae_step_120_mm": round(float(np.mean([s["mae_step_120_mm"] for s in scenario_metrics])), 2),
        "mass_err_vs_solver_pct": round(float(np.mean([s["mass_err_vs_solver_pct"] for s in scenario_metrics])), 2),
        "mass_err_vs_budget_pct": round(float(np.mean([s["mass_err_vs_budget_pct"] for s in scenario_metrics])), 2),
        "avg_rollout_time_s": round(float(np.mean([s["inference_time_s"] for s in scenario_metrics])), 4),
        "scenarios": scenario_metrics,
        "step_mae_mean_mm": (mean_per_step_mae * 1000.0).round(2).tolist(),
        "step_mae_std_mm": (std_per_step_mae * 1000.0).round(2).tolist(),
    }
    return summary


def benchmark_latency(
    model: UNetSurrogate,
    terrain: np.ndarray,
    normalizer: Normalizer,
    cell_size_m: float,
    val_dir: Path,
    device: str = "cpu",
) -> Dict[str, Any]:
    """Measure rollout latency for Batch 1 and Batched inference."""
    rain_arr = np.load(str(val_dir / "rain.npy"))
    params_arr = np.load(str(val_dir / "params.npy"))

    # Batch 1 Benchmark (5 runs)
    single_rain = rain_arr[0]
    single_drain = float(params_arr[0, 3])

    # Warmup
    rollout(model, terrain, single_rain, single_drain, normalizer, cell_size_m=cell_size_m, device=device)

    b1_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        rollout(model, terrain, single_rain, single_drain, normalizer, cell_size_m=cell_size_m, device=device)
        b1_times.append(time.perf_counter() - t0)

    mean_b1_s = float(np.mean(b1_times))
    std_b1_s = float(np.std(b1_times))

    # Batched Benchmark (Batch size 20)
    batch_size = 20
    rain_batch = rain_arr[:batch_size]
    drain_batch = params_arr[:batch_size, 3]

    # Warmup
    rollout_batched(model, terrain, rain_batch[:2], drain_batch[:2], normalizer, cell_size_m=cell_size_m, device=device)

    t0 = time.perf_counter()
    rollout_batched(model, terrain, rain_batch, drain_batch, normalizer, cell_size_m=cell_size_m, device=device)
    total_batch_time_s = time.perf_counter() - t0
    per_scenario_batch_s = total_batch_time_s / batch_size

    speedup_b1 = SOLVER_BASELINE_TIME_S / max(1e-5, mean_b1_s)
    speedup_batched = SOLVER_BASELINE_TIME_S / max(1e-5, per_scenario_batch_s)

    return {
        "solver_reference_s": SOLVER_BASELINE_TIME_S,
        "batch_1_mean_s": round(mean_b1_s, 4),
        "batch_1_mean_ms": round(mean_b1_s * 1000.0, 1),
        "batch_1_std_s": round(std_b1_s, 4),
        "batch_1_speedup": round(speedup_b1, 2),
        "batch_20_total_s": round(total_batch_time_s, 3),
        "batch_20_per_scenario_s": round(per_scenario_batch_s, 4),
        "batch_20_per_scenario_ms": round(per_scenario_batch_s * 1000.0, 1),
        "batch_20_speedup": round(speedup_batched, 2),
    }


def generate_error_plot(
    val_step_mae_mm: List[float],
    val_step_std_mm: List[float],
    extrap_step_mae_mm: List[float],
    extrap_step_std_mm: List[float],
    output_png: Path,
) -> None:
    """Generate and save rollout error trajectory plot."""
    output_png.parent.mkdir(parents=True, exist_ok=True)
    steps = np.arange(1, len(val_step_mae_mm) + 1)

    val_mean = np.array(val_step_mae_mm)
    val_std = np.array(val_step_std_mm)
    extrap_mean = np.array(extrap_step_mae_mm)
    extrap_std = np.array(extrap_step_std_mm)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    # Validation curve
    ax.plot(steps, val_mean, color="#1f77b4", linewidth=2.0, label="Validation (20 Scenarios, 20-150 mm/hr)")
    ax.fill_between(steps, np.maximum(0, val_mean - val_std), val_mean + val_std, color="#1f77b4", alpha=0.2)

    # Extrapolation curve
    ax.plot(steps, extrap_mean, color="#d62728", linewidth=2.0, linestyle="--", label="Extrapolation (10 Scenarios, 150-180 mm/hr)")
    ax.fill_between(steps, np.maximum(0, extrap_mean - extrap_std), extrap_mean + extrap_std, color="#d62728", alpha=0.15)

    # Milestones (10, 30, 60, 120)
    for t_step in [10, 30, 60, 120]:
        if t_step <= len(val_mean):
            val_val = val_mean[t_step - 1]
            ax.scatter([t_step], [val_val], color="#1f77b4", s=35, zorder=5)
            ax.annotate(
                f"t={t_step}m: {val_val:.1f}mm",
                xy=(t_step, val_val),
                xytext=(t_step + 1.5, val_val + 0.4),
                fontsize=8,
                color="#0b4870",
                fontweight="semibold",
            )

    ax.set_title("HydroVision Baseline Surrogate: 120-Step Autoregressive Rollout Error", fontsize=12, pad=12, fontweight="bold")
    ax.set_xlabel("Simulation Step t (Minutes, 1 step = 60s)", fontsize=11)
    ax.set_ylabel("Mean Absolute Depth Error (MAE in mm)", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.set_xlim(1, 120)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", framealpha=0.9)

    plt.tight_layout()
    fig.savefig(str(output_png))
    plt.close(fig)
    print(f"[Evaluation] Saved error plot to: {output_png}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate HydroVision baseline surrogate.")
    parser.add_argument("--checkpoint", type=str, default="artifacts/models/best.pt", help="Path to checkpoint.")
    parser.add_argument("--val-count", type=int, default=20, help="Number of validation scenarios.")
    parser.add_argument("--extrap-count", type=int, default=10, help="Number of extrapolation scenarios.")
    parser.add_argument("--device", type=str, default="cpu", help="Device ('cpu' or 'cuda').")
    parser.add_argument("--threads", type=int, default=8, help="PyTorch CPU threads.")
    parser.add_argument("--output-json", type=str, default="artifacts/reports/baseline_metrics.json", help="Output JSON.")
    parser.add_argument("--output-png", type=str, default="artifacts/reports/baseline_rollout_error.png", help="Output PNG.")

    args = parser.parse_args()
    torch.set_num_threads(args.threads)

    print("=" * 70, flush=True)
    print("HYDROVISION BASELINE SURROGATE EVALUATION", flush=True)
    print(f"Checkpoint: {args.checkpoint} | Device: {args.device.upper()} | Threads: {args.threads}", flush=True)
    print("=" * 70, flush=True)

    # 1. Load Model & Normalizer
    model, normalizer = load_model(args.checkpoint, device=args.device)

    # 2. Load Real Terrain
    terrain_npz = np.load("artifacts/data/terrain.npz")
    terrain = terrain_npz["dem_m"].astype(np.float32)
    cell_size_m = float(terrain_npz["cell_size_m"])

    # 3. Evaluate Validation Split (20 scenarios)
    val_dir = Path(DATA_DIR) / "val"
    print(f"\n[Evaluation] Evaluating {args.val_count} Validation scenarios...", flush=True)
    val_summary = evaluate_split(
        model=model,
        normalizer=normalizer,
        terrain=terrain,
        cell_size_m=cell_size_m,
        split_dir=val_dir,
        num_scenarios=args.val_count,
        device=args.device,
    )

    # 4. Evaluate Extrapolation Split (10 scenarios)
    extrap_dir = Path(DATA_DIR) / "extrapolation"
    print(f"[Evaluation] Evaluating {args.extrap_count} Extrapolation scenarios...", flush=True)
    extrap_summary = evaluate_split(
        model=model,
        normalizer=normalizer,
        terrain=terrain,
        cell_size_m=cell_size_m,
        split_dir=extrap_dir,
        num_scenarios=args.extrap_count,
        device=args.device,
    )

    # 5. Measure Latency & Speedup
    print("[Evaluation] Benchmarking rollout latency...", flush=True)
    latency_summary = benchmark_latency(
        model=model,
        terrain=terrain,
        normalizer=normalizer,
        cell_size_m=cell_size_m,
        val_dir=val_dir,
        device=args.device,
    )

    # 6. Generate Plot
    png_path = Path(args.output_png)
    generate_error_plot(
        val_step_mae_mm=val_summary["step_mae_mean_mm"],
        val_step_std_mm=val_summary["step_mae_std_mm"],
        extrap_step_mae_mm=extrap_summary["step_mae_mean_mm"],
        extrap_step_std_mm=extrap_summary["step_mae_std_mm"],
        output_png=png_path,
    )

    # 7. Package and Save Final Metrics JSON
    report = {
        "status": "COMPLETED",
        "checkpoint": args.checkpoint,
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "validation_summary": {k: v for k, v in val_summary.items() if k not in ("scenarios", "step_mae_mean_mm", "step_mae_std_mm")},
        "extrapolation_summary": {k: v for k, v in extrap_summary.items() if k not in ("scenarios", "step_mae_mean_mm", "step_mae_std_mm")},
        "latency_benchmark": latency_summary,
        "validation_scenarios": val_summary["scenarios"],
        "extrapolation_scenarios": extrap_summary["scenarios"],
    }

    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[Evaluation] Saved metrics report to: {json_path}", flush=True)

    # Print summary table
    print("\n" + "=" * 70, flush=True)
    print("EVALUATION RESULTS SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"Single-Step MAE:        Val = {val_summary['single_step_mae_mm']:5.2f} mm | Extrap = {extrap_summary['single_step_mae_mm']:5.2f} mm")
    print(f"120-Step Rollout MAE:   Val = {val_summary['rollout_mae_mm']:5.2f} mm | Extrap = {extrap_summary['rollout_mae_mm']:5.2f} mm")
    print(f"120-Step Rollout RMSE:  Val = {val_summary['rollout_rmse_mm']:5.2f} mm | Extrap = {extrap_summary['rollout_rmse_mm']:5.2f} mm")
    print(f"Wet IoU (>= 0.05m):     Val = {val_summary['wet_iou']:.4f}   | Extrap = {extrap_summary['wet_iou']:.4f}")
    print(f"Rollout MAE @ Step 10:  Val = {val_summary['mae_step_10_mm']:5.2f} mm | Extrap = {extrap_summary['mae_step_10_mm']:5.2f} mm")
    print(f"Rollout MAE @ Step 30:  Val = {val_summary['mae_step_30_mm']:5.2f} mm | Extrap = {extrap_summary['mae_step_30_mm']:5.2f} mm")
    print(f"Rollout MAE @ Step 60:  Val = {val_summary['mae_step_60_mm']:5.2f} mm | Extrap = {extrap_summary['mae_step_60_mm']:5.2f} mm")
    print(f"Rollout MAE @ Step 120: Val = {val_summary['mae_step_120_mm']:5.2f} mm | Extrap = {extrap_summary['mae_step_120_mm']:5.2f} mm")
    print(f"Mass Error vs Solver:   Val = {val_summary['mass_err_vs_solver_pct']:5.2f} %  | Extrap = {extrap_summary['mass_err_vs_solver_pct']:5.2f} %")
    print(f"Mass Error vs Budget:   Val = {val_summary['mass_err_vs_budget_pct']:5.2f} %  | Extrap = {extrap_summary['mass_err_vs_budget_pct']:5.2f} %")
    print("-" * 70, flush=True)
    print(f"Inference Latency:")
    print(f"  Solver Baseline:      {latency_summary['solver_reference_s']*1000.0:.1f} ms / 120-step scenario")
    print(f"  Surrogate (Batch 1):  {latency_summary['batch_1_mean_ms']:.1f} ms ({latency_summary['batch_1_speedup']}x speedup)")
    print(f"  Surrogate (Batch 20): {latency_summary['batch_20_per_scenario_ms']:.1f} ms/sc ({latency_summary['batch_20_speedup']}x speedup)")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
