"""Batch hydrodynamic simulation script for generating surrogate training datasets.

Phase: Phase 3 (Dataset Generation)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import numpy as np

from hydrovision_ml.config import DT_S, HORIZON_STEPS
from hydrovision_ml.solver.scenarios import make_rain_series, sample_scenarios
from hydrovision_ml.solver.swe_solver import run_solver_core
from hydrovision_ml.terrain.dem import load_terrain, make_synthetic_dem, save_terrain


def generate_dataset(
    n: int = 100,
    seed: int = 42,
    out_dir: str = "artifacts/data",
    stride: int = 1,
) -> Dict[str, str]:
    """Run batch hydrodynamic simulations over sampled scenarios and write train/val/test splits.

    Parameters
    ----------
    n : int
        Number of simulation trajectories to produce (default: 100).
    seed : int
        Random seed for sampling scenarios.
    out_dir : str
        Directory where train.npz, val.npz, and test.npz will be saved.
    stride : int
        Subsampling frame stride for compact storage (default: 1).

    Returns
    -------
    dict
        Paths to created split files.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Ingest or generate terrain
    terrain_file = out_path / "terrain.npz"
    if not terrain_file.is_file():
        dem = make_synthetic_dem()
        save_terrain(dem, output_path=str(terrain_file))
    else:
        loaded = load_terrain(str(terrain_file))
        dem = np.array(loaded["elevation"], dtype=np.float64)

    # Sample Latin Hypercube scenarios
    scenarios = sample_scenarios(n=n, seed=seed)

    all_depths: List[np.ndarray] = []
    all_rain: List[np.ndarray] = []

    print(f"Generating {n} hydrodynamic 2D SWE simulation trajectories...")
    for idx, sc in enumerate(scenarios):
        rain = make_rain_series(
            duration_min=sc["rain_duration_min"],
            intensity_mmhr=sc["rain_intensity_mmhr"],
            shape=sc["rain_shape"],
            dt_s=float(DT_S),
            total_steps=sc["horizon_steps"],
        )
        res = run_solver_core(
            dem=dem,
            rain_series_mmhr=rain,
            dt_s=float(DT_S),
            drain_capacity_mmhr=sc["drain_capacity_mmhr"],
        )

        frames = res["depth_frames"][::stride]  # Subsample if stride > 1
        all_depths.append(frames)
        all_rain.append(np.array(rain, dtype=np.float32))

        if (idx + 1) % max(1, n // 5) == 0 or (idx + 1) == n:
            print(f"  Processed [{idx + 1}/{n}] scenarios (solve time: {res['solve_time_s']}s)")

    depths_arr = np.stack(all_depths, axis=0)  # (N, num_frames, 64, 64)
    rain_arr = np.stack(all_rain, axis=0)      # (N, horizon_steps)

    # Split: 70% train, 15% val, 15% test
    n_train = max(1, int(0.70 * n))
    n_val = max(1, int(0.15 * n))
    n_test = n - n_train - n_val

    indices = np.random.default_rng(seed).permutation(n)
    train_idx = indices[:n_train]
    val_idx = indices[n_train : n_train + n_val]
    test_idx = indices[n_train + n_val :]

    splits = {
        "train": (train_idx, out_path / "train.npz"),
        "val": (val_idx, out_path / "val.npz"),
        "test": (test_idx, out_path / "test.npz"),
    }

    result_paths = {}
    for name, (idxs, split_file) in splits.items():
        np.savez_compressed(
            split_file,
            depth_frames=depths_arr[idxs],
            rain_series=rain_arr[idxs],
            dem=dem.astype(np.float32),
            num_samples=len(idxs),
        )
        result_paths[name] = str(split_file)
        print(f"Saved {name} split: {split_file} ({len(idxs)} samples, shape: {depths_arr[idxs].shape})")

    return result_paths


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate hydrodynamic simulation datasets for surrogate training."
    )
    parser.add_argument("--n", type=int, default=20, help="Number of scenarios to simulate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--out", type=str, default="artifacts/data", help="Output directory path.")
    parser.add_argument("--stride", type=int, default=1, help="Frame subsampling stride.")

    parsed = parser.parse_args(args)
    generate_dataset(n=parsed.n, seed=parsed.seed, out_dir=parsed.out, stride=parsed.stride)


if __name__ == "__main__":
    main(sys.argv[1:])
