import json
import os
from pathlib import Path
import shutil
import sys
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hydrovision_ml.data.generate_dataset import generate_dataset, verify_dataset

def main():
    data_dir = r"C:\hydrovision_data\data"

    # 1. Cache current params.npy for all splits to assert identical scenarios
    splits = ["train", "val", "test", "extrapolation"]
    old_params = {}
    for sp in splits:
        p_path = os.path.join(data_dir, sp, "params.npy")
        if os.path.isfile(p_path):
            old_params[sp] = np.load(p_path)
        else:
            raise FileNotFoundError(f"Missing current params.npy at {p_path}")

    # 2. Check disk space
    total_b, used_b, free_b = shutil.disk_usage(data_dir)
    free_gb = free_b / (1024**3)
    print(f"Free disk space on C: {free_gb:.2f} GB (minimum required: 3.0 GB)")
    if free_gb < 3.0:
        raise RuntimeError(f"Free disk space ({free_gb:.2f} GB) is below 3.0 GB threshold!")

    # 3. Clean old shards if any so full float32 is computed fresh
    shard_dir = os.path.join(data_dir, ".shards")
    if os.path.isdir(shard_dir):
        shutil.rmtree(shard_dir, ignore_errors=True)

    # 4. Run regeneration with max_workers=6
    print("Starting float32 regeneration across 430 scenarios with 6 worker processes...")
    meta = generate_dataset(
        n=400,
        seed=42,
        out_dir=data_dir,
        terrain_path="artifacts/data/terrain.npz",
        n_extrapolation=30,
        max_workers=6,
    )

    # 5. Assert all params.npy match exactly
    for sp in splits:
        new_p_path = os.path.join(data_dir, sp, "params.npy")
        new_p = np.load(new_p_path)
        assert np.array_equal(new_p, old_params[sp]), f"ASSERT FAILED: {sp} params.npy does not match previous run!"
    print("ASSERT SUCCESS: All four splits have 100% identical params.npy to previous run!")

    # 6. Run verification
    stats = verify_dataset(data_dir=data_dir, terrain_path="artifacts/data/terrain.npz")
    print("\n=== DATASET STATS (FLOAT32) ===")
    print("Terrain hash match:", stats["terrain_hash_matches_current"])
    print("Total scenarios:   ", stats["total_scenarios"])
    print("NaN count:         ", stats["nan_count"])
    print("Depth min/max (m): ", stats["depth_min_m"], "/", stats["depth_max_m"])
    print("Wet fraction:      ", stats["wet_fraction_0_05m"])
    print("Mass balance status:", stats["mass_balance"]["status"], "(max rel error:", stats["mass_balance"]["max_relative_error"], ")")

    # 7. Clean temporary shards
    if os.path.isdir(shard_dir):
        shutil.rmtree(shard_dir, ignore_errors=True)
    print("Shards cleaned. Float32 dataset ready.")


if __name__ == "__main__":
    main()
