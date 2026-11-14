"""Batch hydrodynamic simulation script for generating surrogate training datasets.

Phase: Phase 3 (Dataset Generation)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from hydrovision_ml.config import DT_S, HORIZON_STEPS
from hydrovision_ml.solver.scenarios import make_rain_series
from hydrovision_ml.solver.swe_solver import run_solver_core

SHAPE_MAP = {"constant": 0, "triangular": 1, "double_peak": 2}
INV_SHAPE_MAP = {0: "constant", 1: "triangular", 2: "double_peak"}


def compute_terrain_hash(terrain_path: str) -> str:
    """Compute SHA-256 hash of the terrain .npz file."""
    h = hashlib.sha256()
    with open(terrain_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sample_stratified_scenarios(
    n: int,
    seed: int = 42,
    intensity_range: Tuple[float, float] = (20.0, 150.0),
    zero_drain_fraction: float = 0.25,
) -> List[Dict[str, Any]]:
    """Generate stratified rainfall scenarios with controlled parameter distribution.

    Parameters
    ----------
    n : int
        Number of scenarios to generate.
    seed : int
        RNG seed for reproducibility.
    intensity_range : tuple[float, float]
        Min and max rain intensity in mm/hr.
    zero_drain_fraction : float
        Minimum fraction of scenarios that have drain_capacity = 0.0 mm/hr.
    """
    rng = np.random.default_rng(seed)
    shapes = ["constant", "triangular", "double_peak"]
    scenarios: List[Dict[str, Any]] = []

    min_int, max_int = intensity_range
    num_zero_drain = int(round(n * zero_drain_fraction))

    for i in range(n):
        # Stratified rain intensity
        bin_i = (i + rng.uniform(0.05, 0.95)) / n
        intensity = min_int + bin_i * (max_int - min_int)

        # Stratified duration between 15 and 90 min
        bin_d = ((i * 7) % n + rng.uniform(0.05, 0.95)) / n
        duration = 15.0 + bin_d * (90.0 - 15.0)

        # Drain capacity: enforce at least zero_drain_fraction at 0.0
        if i < num_zero_drain:
            drain = 0.0
        else:
            eff_idx = i - num_zero_drain
            eff_n = max(1, n - num_zero_drain)
            bin_drain = ((eff_idx * 13) % eff_n + rng.uniform(0.05, 0.95)) / eff_n
            drain = 0.1 + bin_drain * (30.0 - 0.1)

        shape = shapes[i % len(shapes)]

        scenarios.append(
            {
                "rain_intensity_mmhr": round(float(intensity), 1),
                "rain_duration_min": round(float(duration), 1),
                "rain_shape": shape,
                "drain_capacity_mmhr": round(float(drain), 1),
                "horizon_steps": int(HORIZON_STEPS),
            }
        )

    # Shuffle so splits have balanced distributions
    rng.shuffle(scenarios)
    return scenarios


def _simulate_single_scenario_worker(task: Tuple[int, Dict[str, Any], np.ndarray, float, float, str]) -> Dict[str, Any]:
    """Worker task executed in parallel process.

    Parameters
    ----------
    task : tuple
        (scenario_idx, scenario_dict, dem_array, cell_size_m, dt_s, shard_path)
    """
    idx, sc, dem, cell_size_m, dt_s, shard_path = task

    # Check if shard already exists (resumable with float32 check)
    if os.path.isfile(shard_path) and os.path.getsize(shard_path) > 1000:
        try:
            with np.load(shard_path) as data:
                if data["depth"].dtype == np.float32:
                    return {
                        "idx": idx,
                        "shard_path": shard_path,
                        "solve_time_s": float(data.get("solve_time_s", 0.0)),
                        "cached": True,
                    }
        except Exception:
            pass  # Recompute corrupted shard

    rain_series = make_rain_series(
        duration_min=sc["rain_duration_min"],
        intensity_mmhr=sc["rain_intensity_mmhr"],
        shape=sc["rain_shape"],
        dt_s=dt_s,
        total_steps=sc["horizon_steps"],
    )

    res = run_solver_core(
        dem=dem,
        rain_series_mmhr=rain_series,
        dt_s=dt_s,
        drain_capacity_mmhr=sc["drain_capacity_mmhr"],
        cell_size_m=cell_size_m,
    )

    depth_f32 = res["depth_frames"].astype(np.float32)  # shape (121, 64, 64) in float32
    rain_f32 = np.array(rain_series, dtype=np.float32)   # shape (120,)
    # cum_drain_m3_series is shape (121,) where index 0 is 0.0; steps 1..120 are output steps
    cum_drain_m3 = np.array(res["cum_drain_m3_series"][1:], dtype=np.float32)  # shape (120,)
    params_vec = np.array(
        [
            sc["rain_intensity_mmhr"],
            sc["rain_duration_min"],
            SHAPE_MAP[sc["rain_shape"]],
            sc["drain_capacity_mmhr"],
        ],
        dtype=np.float32,
    )

    # Save individual scenario shard
    os.makedirs(os.path.dirname(shard_path), exist_ok=True)
    temp_shard = f"{shard_path}_{os.getpid()}.tmp.npz"
    np.savez_compressed(
        temp_shard,
        depth=depth_f32,
        rain=rain_f32,
        drain_m3=cum_drain_m3,
        params=params_vec,
        solve_time_s=res["solve_time_s"],
    )
    if os.path.isfile(temp_shard):
        os.replace(temp_shard, shard_path)

    return {
        "idx": idx,
        "shard_path": shard_path,
        "solve_time_s": res["solve_time_s"],
        "cached": False,
    }


def generate_dataset(
    n: int = 400,
    seed: int = 42,
    out_dir: Optional[str] = None,
    terrain_path: str = "artifacts/data/terrain.npz",
    n_extrapolation: int = 30,
    max_workers: Optional[int] = None,
) -> Dict[str, Any]:
    """Run batch hydrodynamic simulations over stratified scenarios on the real DEM.

    Parameters
    ----------
    n : int
        Number of main scenarios (default: 400).
    seed : int
        Random seed for sampling.
    out_dir : str, optional
        Target directory (defaults to HYDRO_DATA_DIR env or C:/hydrovision_data/data).
    terrain_path : str
        Path to terrain.npz.
    n_extrapolation : int
        Number of extreme extrapolation scenarios (default: 30).
    max_workers : int, optional
        Parallel worker count (defaults to CPU count - 2, min 1).
    """
    t_start = time.perf_counter()

    if out_dir is None:
        out_dir = os.getenv("HYDRO_DATA_DIR", r"C:\hydrovision_data\data")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    shard_root = out_path / ".shards"
    shard_root.mkdir(parents=True, exist_ok=True)

    # Ingest real terrain
    terrain_file = Path(terrain_path)
    if not terrain_file.is_file():
        raise FileNotFoundError(f"Terrain file not found: {terrain_file}")

    terrain_hash = compute_terrain_hash(str(terrain_file))
    terrain_data = np.load(str(terrain_file))
    dem = np.array(terrain_data["dem_m"], dtype=np.float64)
    cell_size_m = float(terrain_data["cell_size_m"])
    bounds = [float(b) for b in terrain_data["bounds"]]
    dt_s = float(DT_S)

    print(f"[Dataset] Target directory: {out_path}")
    print(f"[Dataset] Loaded DEM shape: {dem.shape}, cell_size: {cell_size_m:.1f} m, SHA256: {terrain_hash[:12]}...")

    # Sample main scenarios
    main_scenarios = sample_stratified_scenarios(
        n=n, seed=seed, intensity_range=(20.0, 150.0), zero_drain_fraction=0.25
    )

    # Sample extrapolation scenarios (extreme rain: 150-180 mm/hr)
    extrap_scenarios = sample_stratified_scenarios(
        n=n_extrapolation, seed=seed + 999, intensity_range=(150.0, 180.0), zero_drain_fraction=0.25
    )

    # Determine split partitions (70% train, 15% val, 15% test)
    n_train = max(1, int(round(0.70 * n)))
    n_val = max(1, int(round(0.15 * n)))
    n_test = n - n_train - n_val

    split_scenarios: Dict[str, List[Dict[str, Any]]] = {
        "train": main_scenarios[:n_train],
        "val": main_scenarios[n_train : n_train + n_val],
        "test": main_scenarios[n_train + n_val :],
        "extrapolation": extrap_scenarios,
    }

    # Print pre-flight estimate
    total_scenarios = n + n_extrapolation
    bytes_per_scenario = (121 * 64 * 64 * 4) + (120 * 4) + (120 * 4) + (4 * 4)
    est_total_bytes = total_scenarios * bytes_per_scenario
    workers = max_workers or min(6, max(1, (os.cpu_count() or 4) - 2))
    est_time_s = total_scenarios * 0.28 / max(1, workers)
    print("\n" + "=" * 60)
    print("PRE-FLIGHT GENERATION ESTIMATE (FLOAT32):")
    print(f"  Scenarios: {total_scenarios} total (train: {n_train}, val: {n_val}, test: {n_test}, extrap: {n_extrapolation})")
    print(f"  Estimated storage: {est_total_bytes / (1024**2):.1f} MB (limit: 1500 MB)")
    print(f"  Estimated runtime: {est_time_s:.1f} s (~{est_time_s / 60:.1f} min, limit: 45 min)")
    print(f"  Worker processes:  {workers}")
    print("=" * 60 + "\n")

    if est_total_bytes > 1.5 * (1024**3):
        raise RuntimeError(f"Storage estimate ({est_total_bytes / (1024**2):.1f} MB) exceeds 1.5 GB limit!")
    if est_time_s > 45 * 60:
        raise RuntimeError(f"Time estimate ({est_time_s / 60:.1f} min) exceeds 45 minute limit!")

    workers = max_workers or min(6, max(1, (os.cpu_count() or 4) - 2))
    print(f"[Dataset] Executing with {workers} parallel worker processes...")

    # Build work items
    all_tasks = []
    for split_name, sc_list in split_scenarios.items():
        split_shard_dir = shard_root / split_name
        split_shard_dir.mkdir(parents=True, exist_ok=True)
        for idx, sc in enumerate(sc_list):
            shard_path = str(split_shard_dir / f"scenario_{idx:05d}.npz")
            all_tasks.append((idx, sc, dem, cell_size_m, dt_s, shard_path, split_name))

    # Run simulations
    t_sim_start = time.perf_counter()
    done_count = 0
    total_tasks = len(all_tasks)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _simulate_single_scenario_worker,
                (t[0], t[1], t[2], t[3], t[4], t[5]),
            ): (t[6], t[0])
            for t in all_tasks
        }

        for future in as_completed(futures):
            future.result()  # Will raise if worker threw
            done_count += 1
            if done_count % max(1, total_tasks // 10) == 0 or done_count == total_tasks:
                elapsed = time.perf_counter() - t_sim_start
                rate = done_count / max(0.001, elapsed)
                print(f"  [Progress] {done_count}/{total_tasks} scenarios completed ({rate:.1f} sc/s, elapsed: {elapsed:.1f}s)")

    sim_time_s = time.perf_counter() - t_sim_start
    print(f"[Dataset] All simulations finished in {sim_time_s:.2f} s.")

    # Consolidate shards into uncompressed .npy arrays per split
    print("[Dataset] Consolidating shards into uncompressed .npy memory-mappable arrays...")
    manifest_splits: Dict[str, Any] = {}

    for split_name, sc_list in split_scenarios.items():
        num_sc = len(sc_list)
        if num_sc == 0:
            continue
        split_dir = out_path / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        depth_arr = np.empty((num_sc, 121, 64, 64), dtype=np.float32)
        rain_arr = np.empty((num_sc, 120), dtype=np.float32)
        drain_arr = np.empty((num_sc, 120), dtype=np.float32)
        params_arr = np.empty((num_sc, 4), dtype=np.float32)

        split_shard_dir = shard_root / split_name
        for idx in range(num_sc):
            shard_file = split_shard_dir / f"scenario_{idx:05d}.npz"
            with np.load(str(shard_file)) as data:
                depth_arr[idx] = data["depth"]
                rain_arr[idx] = data["rain"]
                drain_arr[idx] = data["drain_m3"]
                params_arr[idx] = data["params"]

        # Write uncompressed .npy files
        depth_file = split_dir / "depth.npy"
        rain_file = split_dir / "rain.npy"
        drain_file = split_dir / "drain_m3.npy"
        params_file = split_dir / "params.npy"
        params_json_file = split_dir / "params.json"

        np.save(str(depth_file), depth_arr)
        np.save(str(rain_file), rain_arr)
        np.save(str(drain_file), drain_arr)
        np.save(str(params_file), params_arr)
        with open(params_json_file, "w", encoding="utf-8") as f:
            json.dump(sc_list, f, indent=2)

        manifest_splits[split_name] = {
            "num_samples": num_sc,
            "depth_shape": list(depth_arr.shape),
            "depth_dtype": str(depth_arr.dtype),
            "files": {
                "depth": f"{split_name}/depth.npy",
                "rain": f"{split_name}/rain.npy",
                "drain_m3": f"{split_name}/drain_m3.npy",
                "params": f"{split_name}/params.npy",
                "params_json": f"{split_name}/params.json",
            },
        }
        print(f"  Saved split '{split_name}': {depth_file} ({num_sc} samples, {os.path.getsize(depth_file) / (1024**2):.1f} MB)")

    total_gen_time = round(time.perf_counter() - t_start, 2)

    # Write metadata.json
    metadata = {
        "dataset_name": "HydroVision Real DEM Surrogates",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "terrain_hash": terrain_hash,
        "terrain_source": str(terrain_data.get("source", "Copernicus GLO-30")),
        "cell_size_m": cell_size_m,
        "bounds": bounds,
        "grid_shape": [64, 64],
        "horizon_steps": int(HORIZON_STEPS),
        "dt_s": dt_s,
        "seed": seed,
        "solver_parameters": {
            "manning_n": 0.035,
            "substep_cfl": 0.7,
            "min_flow_depth_m": 1e-4,
            "boundary": "closed",
        },
        "total_generation_time_s": total_gen_time,
        "split_sizes": {k: v["num_samples"] for k, v in manifest_splits.items()},
        "splits": manifest_splits,
    }

    metadata_path = out_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Dataset] Metadata saved to: {metadata_path}")

    return metadata


def verify_dataset(
    data_dir: Optional[str] = None,
    terrain_path: str = "artifacts/data/terrain.npz",
    report_path: str = "artifacts/reports/dataset_stats.json",
    n_sample_checks: int = 20,
    seed: int = 42,
) -> Dict[str, Any]:
    """Verify physics, mass balance, and numerical integrity of generated dataset."""
    if data_dir is None:
        data_dir = os.getenv("HYDRO_DATA_DIR", r"C:\hydrovision_data\data")

    data_path = Path(data_dir)
    meta_path = data_path / "metadata.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 1. Terrain Hash Verification
    current_terrain_hash = compute_terrain_hash(terrain_path)
    meta_terrain_hash = meta["terrain_hash"]
    terrain_hash_match = current_terrain_hash == meta_terrain_hash
    if not terrain_hash_match:
        raise ValueError(
            f"Terrain hash MISMATCH! Current: {current_terrain_hash} vs Metadata: {meta_terrain_hash}"
        )

    # Load terrain
    terrain_data = np.load(terrain_path)
    cell_size_m = float(terrain_data["cell_size_m"])
    cell_area = cell_size_m ** 2
    domain_area = 64 * 64 * cell_area

    # Check each split
    split_stats = {}
    rng = np.random.default_rng(seed)

    all_depth_mins = []
    all_depth_maxs = []
    all_nan_counts = 0
    all_wet_cell_counts = 0
    all_total_cell_counts = 0
    mass_balance_errors = []

    for split_name, sinfo in meta["splits"].items():
        depth_path = data_path / sinfo["files"]["depth"]
        rain_path = data_path / sinfo["files"]["rain"]
        drain_path = data_path / sinfo["files"]["drain_m3"]

        # Memory-map depth array (zero-copy / low memory footprint)
        depth_mmap = np.load(str(depth_path), mmap_mode="r")
        rain_arr = np.load(str(rain_path))
        drain_arr = np.load(str(drain_path))

        num_sc = sinfo["num_samples"]
        assert depth_mmap.shape == (num_sc, 121, 64, 64), f"Unexpected shape: {depth_mmap.shape}"
        assert depth_mmap.dtype == np.float32, f"Unexpected dtype: {depth_mmap.dtype}"
        assert rain_arr.shape == (num_sc, 120), f"Unexpected rain shape: {rain_arr.shape}"
        assert drain_arr.shape == (num_sc, 120), f"Unexpected drain shape: {drain_arr.shape}"

        # Sample scenarios for detailed mass balance verification
        n_check = min(num_sc, max(2, n_sample_checks // len(meta["splits"])))
        sample_indices = rng.choice(num_sc, size=n_check, replace=False)

        for idx in sample_indices:
            depth_traj = np.array(depth_mmap[idx], dtype=np.float64)  # (121, 64, 64)
            rain = rain_arr[idx]                                      # (120,)
            drained = drain_arr[idx]                                  # (120,)

            # Check no NaNs
            nan_cnt = int(np.isnan(depth_traj).sum())
            all_nan_counts += nan_cnt
            assert nan_cnt == 0, f"NaNs detected in split {split_name} sample {idx}"

            # Check non-negativity
            min_d = float(np.min(depth_traj))
            max_d = float(np.max(depth_traj))
            all_depth_mins.append(min_d)
            all_depth_maxs.append(max_d)
            assert min_d >= -1e-4, f"Negative depth {min_d} in split {split_name} sample {idx}"

            # Check wet cells (>= 0.05m)
            wet_cells = int((depth_traj >= 0.05).sum())
            total_cells = depth_traj.size
            all_wet_cell_counts += wet_cells
            all_total_cell_counts += total_cells

            # Mass balance at final step (step 120)
            total_rain_vol = float(np.sum(rain / 3600000.0 * 60.0)) * domain_area
            total_drained_vol = float(drained[-1])
            stored_vol = float(np.sum(depth_traj[-1])) * cell_area
            expected_stored = total_rain_vol - total_drained_vol
            rel_err = abs(stored_vol - expected_stored) / max(total_rain_vol, 1.0)
            mass_balance_errors.append(rel_err)

        split_stats[split_name] = {
            "num_samples": num_sc,
            "checked_samples": int(n_check),
        }

    overall_stats = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "terrain_hash": meta_terrain_hash,
        "terrain_hash_matches_current": terrain_hash_match,
        "total_scenarios": sum(s["num_samples"] for s in meta["splits"].values()),
        "nan_count": all_nan_counts,
        "depth_min_m": float(min(all_depth_mins)),
        "depth_max_m": float(max(all_depth_maxs)),
        "wet_fraction_0_05m": round(float(all_wet_cell_counts / max(1, all_total_cell_counts)), 4),
        "mass_balance": {
            "checked_samples_count": len(mass_balance_errors),
            "max_relative_error": float(np.max(mass_balance_errors)),
            "mean_relative_error": float(np.mean(mass_balance_errors)),
            "status": "PASS" if np.max(mass_balance_errors) < 0.005 else "FAIL",
        },
        "splits": split_stats,
    }

    report_p = Path(report_path)
    report_p.parent.mkdir(parents=True, exist_ok=True)
    with open(report_p, "w", encoding="utf-8") as f:
        json.dump(overall_stats, f, indent=2)
    print(f"\n[Verification] Saved dataset stats to: {report_p}")

    return overall_stats


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate hydrodynamic simulation datasets on real DEM for surrogate training."
    )
    parser.add_argument("--n", type=int, default=400, help="Number of scenarios to simulate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--out",
        type=str,
        default=os.getenv("HYDRO_DATA_DIR", r"C:\hydrovision_data\data"),
        help="Output directory path.",
    )
    parser.add_argument(
        "--terrain",
        type=str,
        default="artifacts/data/terrain.npz",
        help="Path to conditioned real terrain.",
    )
    parser.add_argument(
        "--extrap",
        type=int,
        default=30,
        help="Number of extrapolation scenarios.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run integrity verification on existing dataset.",
    )

    parsed = parser.parse_args(args)

    if not parsed.verify_only:
        generate_dataset(
            n=parsed.n,
            seed=parsed.seed,
            out_dir=parsed.out,
            terrain_path=parsed.terrain,
            n_extrapolation=parsed.extrap,
        )

    stats = verify_dataset(
        data_dir=parsed.out,
        terrain_path=parsed.terrain,
    )
    print("\n" + "=" * 60)
    print("DATASET INTEGRITY & PHYSICS VERIFICATION SUMMARY:")
    print(f"  Terrain SHA256 Match: {stats['terrain_hash_matches_current']}")
    print(f"  Total Scenarios:      {stats['total_scenarios']}")
    print(f"  NaN Count:            {stats['nan_count']}")
    print(f"  Depth Min / Max:      {stats['depth_min_m']:.4f} m / {stats['depth_max_m']:.4f} m")
    print(f"  Wet Cell Fraction:    {stats['wet_fraction_0_05m'] * 100:.2f}% (>= 0.05m)")
    print(f"  Max Mass Rel Error:   {stats['mass_balance']['max_relative_error']:.6e} ({stats['mass_balance']['status']})")
    print("=" * 60)


if __name__ == "__main__":
    main(sys.argv[1:])
