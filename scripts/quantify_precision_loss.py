import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from hydrovision_ml.solver.swe_solver import run_solver_core
from hydrovision_ml.solver.scenarios import make_rain_series

# Load real terrain
terrain = np.load("artifacts/data/terrain.npz")
dem = terrain["dem_m"]
dx = float(terrain["cell_size_m"])

# Load stored train dataset
with open("C:/hydrovision_data/data/train/params.json", "r") as f:
    scenarios = json.load(f)

depth_stored_mmap = np.load("C:/hydrovision_data/data/train/depth.npy", mmap_mode="r")

max_errors = []
mean_wet_errors = []
sub_2mm_fraction_list = []

for i in range(10):
    sc = scenarios[i]
    stored_f16 = depth_stored_mmap[i]  # (121, 64, 64) float16

    rain = make_rain_series(
        duration_min=sc["rain_duration_min"],
        intensity_mmhr=sc["rain_intensity_mmhr"],
        shape=sc["rain_shape"],
        dt_s=60.0,
        total_steps=120,
    )
    res = run_solver_core(
        dem=dem,
        rain_series_mmhr=rain,
        dt_s=60.0,
        drain_capacity_mmhr=sc["drain_capacity_mmhr"],
        cell_size_m=dx,
    )
    solver_f32 = res["depth_frames"]  # (121, 64, 64) float32

    abs_diff = np.abs(solver_f32 - stored_f16.astype(np.float32))
    max_errors.append(float(np.max(abs_diff)))

    wet_mask = solver_f32 >= 0.05
    if np.any(wet_mask):
        mean_wet_errors.append(float(np.mean(abs_diff[wet_mask])))

    step_diffs = np.abs(np.diff(solver_f32, axis=0))  # (120, 64, 64)
    non_zero = step_diffs > 1e-5
    if np.any(non_zero):
        sub_2mm = step_diffs[non_zero] < 0.002  # < 2 mm
        sub_2mm_fraction_list.append(float(np.mean(sub_2mm)))

print("=== FLOAT16 PRECISION QUANTIFICATION (10 TRAIN SCENARIOS) ===")
print("Max Absolute Error:                 %.6f m (%.2f mm)" % (max(max_errors), max(max_errors)*1000))
print("Mean Absolute Error (Wet Cells):     %.6f m (%.3f mm)" % (float(np.mean(mean_wet_errors)), float(np.mean(mean_wet_errors))*1000))
print("Fraction of per-step changes < 2 mm: %.2f%%" % (float(np.mean(sub_2mm_fraction_list))*100))
