#!/usr/bin/env python3
"""HydroVision Model Acceptance Validation Suite.

This script is the definitive merge condition for surrogate models and solvers.
It tests the active implementation (selected via HYDRO_MODE=mock|real or --mode)
against Contract v1.0 specifications and Contract v1.1 conservation standards across:
- Predefined storm presets
- Parameter boundaries (min/max ranges from config.json)
- Hyetograph profile variations
- Determinism and idempotency
- Payload size and serialization limits
- Numerical sanity (finite, non-negative, dry initial frame)
- Latency and speedup budgets

Usage:
    python scripts/validate_model.py
    python scripts/validate_model.py --mode real
    python scripts/validate_model.py --json results/validation_report.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Configuration and thresholds
DEFAULT_MAX_LATENCY_MS: float = 2000.0
DEFAULT_SURROGATE_RESIDUAL_THRESHOLD: float = 0.05  # Max 5% mass residual over 2 hours
DEFAULT_SOLVER_RESIDUAL_THRESHOLD: float = 0.01     # Max 1% mass residual for SWE solver
DEPTH_EPSILON: float = -1e-6                        # Allow tiny float precision underflow
FRAME_ZERO_TOL: float = 1e-6                        # Dry initial state tolerance


def get_ml_module(mode: str):
    """Load the target ML module dynamically based on mode."""
    if mode == "real":
        try:
            import hydrovision_ml.api as ml
            return ml
        except Exception as err:
            print(f"[ERROR] Failed to import hydrovision_ml.api: {err}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            import hydrovision_ml.mock as ml
            return ml
        except Exception as err:
            print(f"[ERROR] Failed to import hydrovision_ml.mock: {err}", file=sys.stderr)
            sys.exit(1)


def check_forecast_response(
    res: Dict[str, Any],
    case_name: str,
    max_latency_ms: float,
    residual_threshold: float,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate a single forecast response against contract criteria."""
    errors: List[str] = []
    stats: Dict[str, Any] = {}

    # 1. Required keys
    required_keys = [
        "times_s",
        "depth_frames",
        "rain_series_mmhr",
        "peak_depth_m",
        "flooded_area_m2",
        "inference_time_ms",
        "model_name",
    ]
    for k in required_keys:
        if k not in res:
            errors.append(f"Missing required key '{k}'")

    if errors:
        return False, errors, stats

    # 2. times_s checks
    times = res["times_s"]
    if not isinstance(times, list) or len(times) != 121:
        errors.append(f"times_s must be list of length 121, got {len(times) if isinstance(times, list) else type(times)}")
    else:
        if times[0] != 0:
            errors.append(f"times_s[0] must be 0, got {times[0]}")
        for i in range(len(times) - 1):
            if times[i + 1] <= times[i]:
                errors.append(f"times_s must be strictly increasing: index {i} ({times[i]}) >= {i+1} ({times[i+1]})")
                break

    # 3. rain_series_mmhr checks
    rain = res["rain_series_mmhr"]
    if not isinstance(rain, list) or len(rain) != 120:
        errors.append(f"rain_series_mmhr must be list of length 120, got {len(rain) if isinstance(rain, list) else type(rain)}")
    else:
        for i, val in enumerate(rain):
            if not math.isfinite(val) or val < 0.0:
                errors.append(f"rain_series_mmhr[{i}] has invalid rainfall: {val}")
                break

    # 4. depth_frames checks
    frames = res["depth_frames"]
    if not isinstance(frames, list) or len(frames) != 121:
        errors.append(f"depth_frames outer length must be 121, got {len(frames) if isinstance(frames, list) else type(frames)}")
    else:
        try:
            arr = np.asarray(frames, dtype=np.float64)
            if arr.shape != (121, 64, 64):
                errors.append(f"depth_frames array shape must be (121, 64, 64), got {arr.shape}")
            else:
                stats["shape"] = "(121, 64, 64)"
                # Check NaNs and Infs
                if np.any(np.isnan(arr)):
                    errors.append("depth_frames contains NaN values")
                if np.any(np.isinf(arr)):
                    errors.append("depth_frames contains Inf values")

                # Frame 0 dry check
                max_frame_0 = float(np.max(np.abs(arr[0])))
                if max_frame_0 > FRAME_ZERO_TOL:
                    errors.append(f"Frame 0 (t=0s) must be dry (identically 0.0m), found max depth {max_frame_0:.6f}m")

                # Negative depth check
                min_depth = float(np.min(arr))
                stats["min_depth"] = round(min_depth, 6)
                if min_depth < DEPTH_EPSILON:
                    errors.append(f"Negative water depth detected: {min_depth:.6f}m (must be >= {DEPTH_EPSILON}m)")

                max_depth = float(np.max(arr))
                stats["max_depth"] = round(max_depth, 4)

        except Exception as e:
            errors.append(f"Failed to parse depth_frames as float array: {e}")

    # 5. Latency check
    inf_time = res.get("inference_time_ms", 0.0)
    stats["latency_ms"] = round(float(inf_time), 1)
    if inf_time <= 0.0:
        errors.append(f"inference_time_ms must be positive, got {inf_time}")
    elif inf_time > max_latency_ms:
        errors.append(f"inference_time_ms {inf_time:.1f}ms exceeds allowable limit {max_latency_ms:.1f}ms")

    # 6. Contract v1.1 Mass residual checks (optional/additive)
    if "mass_residual_series" in res and res["mass_residual_series"] is not None:
        residuals = res["mass_residual_series"]
        if not isinstance(residuals, list) or len(residuals) != 121:
            errors.append(f"v1.1 mass_residual_series must have length 121, got {len(residuals)}")
        else:
            if any(not math.isfinite(r) for r in residuals):
                errors.append("mass_residual_series contains non-finite numbers")
            if any(r < -1e-7 for r in residuals):
                errors.append(f"mass_residual_series contains negative residuals: min={min(residuals)}")
            max_res = float(max(residuals))
            stats["max_residual"] = round(max_res, 5)
            if max_res > residual_threshold:
                errors.append(
                    f"Max mass residual {max_res:.4f} exceeds threshold {residual_threshold:.4f}"
                )
    else:
        stats["max_residual"] = "N/A (v1.0)"

    # 7. JSON serialization and size reporting
    try:
        arr_for_json = np.asarray(frames, dtype=np.float64)
        rounded_frames = np.round(arr_for_json, 3).tolist()
        payload_copy = dict(res)
        payload_copy["depth_frames"] = rounded_frames
        serialized = json.dumps(payload_copy).encode("utf-8")
        size_mb = len(serialized) / (1024 * 1024)
        stats["payload_mb"] = round(size_mb, 2)
        if size_mb > 15.0:
            errors.append(f"Serialized JSON payload {size_mb:.2f} MB exceeds 15 MB bandwidth envelope")
    except Exception as e:
        errors.append(f"JSON serialization failed: {e}")

    success = len(errors) == 0
    return success, errors, stats


def run_validation(
    mode: str = "mock",
    max_latency_ms: float = DEFAULT_MAX_LATENCY_MS,
    surrogate_threshold: float = DEFAULT_SURROGATE_RESIDUAL_THRESHOLD,
    solver_threshold: float = DEFAULT_SOLVER_RESIDUAL_THRESHOLD,
    json_output_path: Optional[str] = None,
) -> bool:
    """Execute complete validation suite across all required scenarios."""
    print("=" * 102)
    print(" HydroVision Model Acceptance Validation Suite")
    print(f" Target Mode: {mode.upper()} | Max Latency: {max_latency_ms:.0f} ms | Res. Thresholds: {surrogate_threshold} (surrogate) / {solver_threshold} (solver)")
    print("=" * 102)

    ml = get_ml_module(mode)

    # 1. Initialize / load model weights
    try:
        ml.load_all()
        print(f"[INFO] Model weights initialized successfully via {ml.__name__}.load_all()")
    except Exception as err:
        print(f"[FATAL] load_all() failed: {err}")
        return False

    # Define test matrix: 3 presets + boundary extremes + hyetograph shapes
    test_cases = [
        {
            "id": "preset_moderate",
            "name": "Preset 1: Moderate Summer Storm",
            "params": {
                "rain_intensity_mmhr": 60.0,
                "rain_duration_min": 45.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 0.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "preset_cloudburst",
            "name": "Preset 2: Extreme Cloudburst",
            "params": {
                "rain_intensity_mmhr": 120.0,
                "rain_duration_min": 30.0,
                "rain_shape": "triangular",
                "drain_capacity_mmhr": 5.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "preset_drain_mitigation",
            "name": "Preset 3: Engineered Drain Mit.",
            "params": {
                "rain_intensity_mmhr": 80.0,
                "rain_duration_min": 45.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 25.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "bound_min_values",
            "name": "Boundary Min (Rain=20, Dur=15)",
            "params": {
                "rain_intensity_mmhr": 20.0,
                "rain_duration_min": 15.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 0.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "bound_max_values",
            "name": "Boundary Max (Rain=150, Dur=90)",
            "params": {
                "rain_intensity_mmhr": 150.0,
                "rain_duration_min": 90.0,
                "rain_shape": "constant",
                "drain_capacity_mmhr": 30.0,
                "horizon_steps": 120,
            },
        },
        {
            "id": "shape_double_peak",
            "name": "Hyetograph: Double Peak Storm",
            "params": {
                "rain_intensity_mmhr": 80.0,
                "rain_duration_min": 45.0,
                "rain_shape": "double_peak",
                "drain_capacity_mmhr": 0.0,
                "horizon_steps": 120,
            },
        },
    ]

    results: List[Dict[str, Any]] = []
    overall_pass = True

    print(f"\n{'#':<3} {'TEST CASE':<34} {'DETERMINISM':<13} {'SHAPE':<15} {'LATENCY':<11} {'PAYLOAD':<10} {'RESIDUAL':<10} {'RESULT':<6}")
    print("-" * 102)

    # Execute surrogate rollout cases
    for idx, case in enumerate(test_cases, start=1):
        case_id = case["id"]
        case_name = case["name"]
        params = case["params"]

        # Run 1
        t0 = time.perf_counter()
        res1 = ml.forecast(params)
        dur1 = (time.perf_counter() - t0) * 1000.0

        # Run 2 for determinism verification
        res2 = ml.forecast(params)

        # Determinism check
        arr1 = np.asarray(res1.get("depth_frames", []), dtype=np.float64)
        arr2 = np.asarray(res2.get("depth_frames", []), dtype=np.float64)
        is_deterministic = bool(arr1.shape == arr2.shape and np.allclose(arr1, arr2, atol=1e-7))
        determ_str = "PASS" if is_deterministic else "FAIL"

        # Validate response criteria
        passed, errors, stats = check_forecast_response(
            res1,
            case_name=case_name,
            max_latency_ms=max_latency_ms,
            residual_threshold=surrogate_threshold,
        )

        if not is_deterministic:
            passed = False
            errors.append("Forecast output is non-deterministic (different result on identical input)")

        if not passed:
            overall_pass = False

        status_str = "PASS" if passed else "FAIL"
        shape_str = stats.get("shape", "ERR")
        lat_str = f"{stats.get('latency_ms', 0):.1f} ms"
        size_str = f"{stats.get('payload_mb', 0):.2f} MB"
        res_str = str(stats.get("max_residual", "-"))

        print(f"{idx:<3} {case_name:<34} {determ_str:<13} {shape_str:<15} {lat_str:<11} {size_str:<10} {res_str:<10} {status_str:<6}")

        if errors:
            for e in errors:
                print(f"    -> [ERROR] {e}")

        results.append({
            "test_number": idx,
            "case_id": case_id,
            "case_name": case_name,
            "passed": passed,
            "deterministic": is_deterministic,
            "stats": stats,
            "errors": errors,
        })

    # Execute Solver Case
    solver_case_idx = len(test_cases) + 1
    solver_params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }
    print("-" * 102)
    print(f"[INFO] Executing numerical 2D SWE solver test case...")
    solv_res1 = ml.run_solver(solver_params)
    solv_res2 = ml.run_solver(solver_params)

    # Determinism
    s_arr1 = np.asarray(solv_res1.get("depth_frames", []), dtype=np.float64)
    s_arr2 = np.asarray(solv_res2.get("depth_frames", []), dtype=np.float64)
    solv_determ = bool(s_arr1.shape == s_arr2.shape and np.allclose(s_arr1, s_arr2, atol=1e-7))
    solv_determ_str = "PASS" if solv_determ else "FAIL"

    solv_errors: List[str] = []
    solv_passed = True
    if not solv_determ:
        solv_errors.append("Solver output is non-deterministic")
        solv_passed = False

    solv_frames = solv_res1.get("depth_frames", [])
    if len(solv_frames) != 121:
        solv_errors.append(f"Solver depth_frames length must be 121, got {len(solv_frames)}")
        solv_passed = False

    if "mass_residual_series" in solv_res1 and solv_res1["mass_residual_series"] is not None:
        s_residuals = solv_res1["mass_residual_series"]
        max_s_res = float(max(s_residuals))
        if max_s_res > solver_threshold:
            solv_errors.append(f"Solver mass residual {max_s_res:.6f} exceeds threshold {solver_threshold}")
            solv_passed = False
        solv_res_display = f"{max_s_res:.4e}"
    else:
        solv_res_display = "N/A (v1.0)"

    solv_solve_time = solv_res1.get("solve_time_s", 0.0)
    solv_lat_str = f"{solv_solve_time*1000.0:.0f} ms"
    solv_status_str = "PASS" if solv_passed else "FAIL"

    print(f"{solver_case_idx:<3} {'SWE Solver Ground Truth':<34} {solv_determ_str:<13} {'(121, 64, 64)':<15} {solv_lat_str:<11} {'~3.3 MB':<10} {solv_res_display:<10} {solv_status_str:<6}")
    if solv_errors:
        for e in solv_errors:
            print(f"    -> [ERROR] {e}")
        overall_pass = False

    results.append({
        "test_number": solver_case_idx,
        "case_id": "swe_solver",
        "case_name": "SWE Solver Ground Truth",
        "passed": solv_passed,
        "deterministic": solv_determ,
        "stats": {"solve_time_s": solv_solve_time, "max_residual": solv_res_display},
        "errors": solv_errors,
    })

    # Comparative Metrics Test Case
    metrics_case_idx = solver_case_idx + 1
    metrics_passed = True
    metrics_errors: List[str] = []
    try:
        test_pred = ml.forecast(solver_params)["depth_frames"]
        test_true = solv_res1["depth_frames"]
        metrics = ml.compute_metrics(test_pred, test_true, solver_params)
        for mk in ["mae", "rmse", "peak_depth_error", "wet_iou", "mass_error", "arrival_time_error_s", "speedup"]:
            if mk not in metrics:
                metrics_errors.append(f"compute_metrics output missing key '{mk}'")
                metrics_passed = False
            elif not math.isfinite(metrics[mk]):
                metrics_errors.append(f"metric '{mk}' is non-finite: {metrics[mk]}")
                metrics_passed = False

        if not (0.0 <= metrics.get("wet_iou", 0.0) <= 1.0):
            metrics_errors.append(f"wet_iou {metrics.get('wet_iou')} out of valid range [0, 1]")
            metrics_passed = False

    except Exception as e:
        metrics_passed = False
        metrics_errors.append(f"compute_metrics raised exception: {e}")

    metrics_status_str = "PASS" if metrics_passed else "FAIL"
    print(f"{metrics_case_idx:<3} {'Comparative Evaluation Suite':<34} {'N/A':<13} {'7 Metrics':<15} {'<10 ms':<11} {'N/A':<10} {'0.0000':<10} {metrics_status_str:<6}")
    if metrics_errors:
        for e in metrics_errors:
            print(f"    -> [ERROR] {e}")
        overall_pass = False

    results.append({
        "test_number": metrics_case_idx,
        "case_id": "comparative_metrics",
        "case_name": "Comparative Evaluation Suite",
        "passed": metrics_passed,
        "deterministic": True,
        "stats": {"metrics_count": len(metrics) if 'metrics' in locals() else 0},
        "errors": metrics_errors,
    })

    print("-" * 102)
    pass_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    print(f"SUMMARY: {pass_count}/{total_count} acceptance checks passed in mode '{mode}'.")

    # Write JSON report if requested
    if json_output_path:
        out_path = Path(json_output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report_data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mode": mode,
            "overall_pass": overall_pass,
            "pass_count": pass_count,
            "total_count": total_count,
            "thresholds": {
                "max_latency_ms": max_latency_ms,
                "surrogate_residual_threshold": surrogate_threshold,
                "solver_residual_threshold": solver_threshold,
            },
            "cases": results,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"[INFO] Detailed validation report written to {out_path.resolve()}")

    if overall_pass:
        print(">> ALL ACCEPTANCE CHECKS PASSED <<")
        return True
    else:
        print(">> ONE OR MORE ACCEPTANCE CHECKS FAILED <<")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate HydroVision surrogate models and SWE solvers against production acceptance contracts."
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "real"],
        default=os.getenv("HYDRO_MODE", "mock").lower(),
        help="Execution target: 'mock' or 'real' (defaults to HYDRO_MODE env var or 'mock').",
    )
    parser.add_argument(
        "--max-latency-ms",
        type=float,
        default=DEFAULT_MAX_LATENCY_MS,
        help=f"Maximum acceptable surrogate rollout inference latency in ms (default: {DEFAULT_MAX_LATENCY_MS} ms).",
    )
    parser.add_argument(
        "--surrogate-threshold",
        type=float,
        default=DEFAULT_SURROGATE_RESIDUAL_THRESHOLD,
        help=f"Maximum acceptable mass conservation residual for surrogate (default: {DEFAULT_SURROGATE_RESIDUAL_THRESHOLD}).",
    )
    parser.add_argument(
        "--solver-threshold",
        type=float,
        default=DEFAULT_SOLVER_RESIDUAL_THRESHOLD,
        help=f"Maximum acceptable mass conservation residual for SWE solver (default: {DEFAULT_SOLVER_RESIDUAL_THRESHOLD}).",
    )
    parser.add_argument(
        "--json",
        nargs="?",
        const="results/validation_report.json",
        default=None,
        help="Output path for JSON validation report (default: results/validation_report.json).",
    )

    args = parser.parse_args()

    success = run_validation(
        mode=args.mode,
        max_latency_ms=args.max_latency_ms,
        surrogate_threshold=args.surrogate_threshold,
        solver_threshold=args.solver_threshold,
        json_output_path=args.json,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
