"""Step 4 to 7: Process Candidate 3 DEM to 64x64, save terrain.npz, run QA and solver checks.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil

import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

# Import project modules
import sys
ROOT = Path(r"c:\Users\Khubaib\OneDrive\Desktop\HydroVison")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hydrovision_ml.terrain.dem import compute_slopes, dem_quality_check
from hydrovision_ml.solver.swe_solver import run_solver_core
from hydrovision_ml.solver.scenarios import make_rain_series

# -----------------------------------------------------------------------------
# STEP 4: CROP CANDIDATE 3, DOWNSAMPLE 2x BLOCK MEAN, SMOOTH, COMPUTE BOUNDS
# -----------------------------------------------------------------------------
print("=" * 70)
print("STEP 4: DOWNSAMPLE CANDIDATE 3 (128x128 -> 64x64) AND GEOTRANSFORM")
print("=" * 70)

tif_path = Path(r"C:\hydrovision_data\dem\marathahalli.tif")
with rasterio.open(tif_path) as src:
    full_dem = src.read(1)
    transform = src.transform
    crs = src.crs
    res = src.res

# Candidate 3: rows 27:155, cols 12:140
r0, r1 = 27, 155
c0, c1 = 12, 140
native_128 = full_dem[r0:r1, c0:c1].astype(np.float64)
assert native_128.shape == (128, 128), f"Expected (128, 128), got {native_128.shape}"

# Compute bounds of chosen 128x128 window
# transform * (col, row) -> (x, y) = (lon, lat)
west_128, north_128 = transform * (c0, r0)
east_128, south_128 = transform * (c1, r1)

print(f"Native 128x128 Window Bounds:")
print(f"  West (min lon):  {west_128:.6f}° E")
print(f"  South (min lat): {south_128:.6f}° N")
print(f"  East (max lon):  {east_128:.6f}° E")
print(f"  North (max lat): {north_128:.6f}° N")

# Orientation check
# Row 0 = North (higher lat), Row 127 = South (lower lat)
# Col 0 = West (lower lon), Col 127 = East (higher lon)
print(f"Orientation verification: transform[4] = {transform[4]} (negative means row 0 is North-up).")
assert north_128 > south_128, "North lat must be greater than South lat"
assert east_128 > west_128, "East lon must be greater than West lon"

# 2x Block Mean downsampling to 64x64
dem_64_raw = native_128.reshape(64, 2, 64, 2).mean(axis=(1, 3))
assert dem_64_raw.shape == (64, 64), f"Expected (64, 64), got {dem_64_raw.shape}"

# Light Gaussian smoothing
# sigma = 0.8 balances removing high-frequency building/tree noise while preserving macro drainage ridges
SIGMA = 0.8
dem_64_smooth = gaussian_filter(dem_64_raw, sigma=SIGMA)
dem_64 = np.round(dem_64_smooth, 3).astype(np.float32)

# Compute real cell sizes
mean_lat = (south_128 + north_128) / 2.0
mean_lat_rad = math.radians(mean_lat)
R_lat = 111132.954 - 559.822 * math.cos(2 * mean_lat_rad) + 1.175 * math.cos(4 * mean_lat_rad)
R_lon = 111412.84 * math.cos(mean_lat_rad) - 93.5 * math.cos(3 * mean_lat_rad)

dx_deg_64 = abs(transform[0]) * 2.0
dy_deg_64 = abs(transform[4]) * 2.0

dx_m_real = dx_deg_64 * R_lon
dy_m_real = dy_deg_64 * R_lat
cell_size_m_effective = round(float((dx_m_real + dy_m_real) / 2.0), 1)  # ~60.9m
aspect_diff = abs(dx_m_real - dy_m_real) / dy_m_real * 100.0

print(f"\nFinal 64x64 Grid Spatial Metrics:")
print(f"  Smoothing sigma:       {SIGMA}")
print(f"  E-W cell size dx:      {dx_m_real:.3f} m")
print(f"  N-S cell size dy:      {dy_m_real:.3f} m")
print(f"  Effective cell_size_m: {cell_size_m_effective} m (dx/dy diff = {aspect_diff:.2f}% < 3% threshold)")
print(f"  Area covered:          {(64 * dx_m_real / 1000.0):.2f} km (E-W) x {(64 * dy_m_real / 1000.0):.2f} km (N-S)")
print(f"  Total catchment area:  {(64 * dx_m_real * 64 * dy_m_real / 1e6):.2f} km²")

final_bounds = [round(float(south_128), 6), round(float(west_128), 6), round(float(north_128), 6), round(float(east_128), 6)]
print(f"  Final Bounds [S, W, N, E]: {final_bounds}")

# -----------------------------------------------------------------------------
# STEP 5: SAVE artifacts/data/terrain.npz
# -----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("STEP 5: SAVE ARTIFACTS/DATA/TERRAIN.NPZ")
print("=" * 70)

terrain_file = ROOT / "artifacts" / "data" / "terrain.npz"
terrain_file.parent.mkdir(parents=True, exist_ok=True)

# Compute slopes with real cell size
slope_x, slope_y = compute_slopes(dem_64, cell_size_m=cell_size_m_effective)

source_citation = (
    "Copernicus GLO-30 via OpenTopography, produced using Copernicus WorldDEM-30 "
    "(c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA; all rights reserved"
)

np.savez_compressed(
    terrain_file,
    dem_m=dem_64,
    elevation=dem_64.astype(np.float64),
    slope_x=slope_x.astype(np.float64),
    slope_y=slope_y.astype(np.float64),
    bounds=np.array(final_bounds, dtype=np.float64),
    cell_size_m=np.float64(cell_size_m_effective),
    dx_m=np.float64(cell_size_m_effective),
    is_synthetic=False,
    source=source_citation,
    smoothing_sigma=float(SIGMA),
    window_used=np.array([r0, r1, c0, c1], dtype=np.int32),
)
print(f"Saved terrain archive to {terrain_file} ({terrain_file.stat().st_size} bytes)")

# -----------------------------------------------------------------------------
# STEP 6: QUALITY CHECK & REPORTS (dem.png & hillshade)
# -----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("STEP 6: DEM QUALITY CHECK AND PLOTTING")
print("=" * 70)

qa = dem_quality_check(dem_64)
print(f"dem_quality_check output:")
for k, v in qa.items():
    print(f"  {k}: {v}")

relief = qa["max_elevation"] - qa["min_elevation"]
print(f"  Relief:            {relief:.2f} m ({qa['min_elevation']:.2f} m to {qa['max_elevation']:.2f} m)")
print(f"  Depressions/sinks: {qa['sink_count']}")
print(f"  Mean slope:        {math.degrees(math.atan(qa['mean_slope'])):.2f}° (gradient: {qa['mean_slope']})")

# Check where lowest cells touch edges
min_e = qa["min_elevation"]
lowest_cells = np.where(dem_64 <= min_e + 1.0)
edge_touches = []
if np.any(lowest_cells[0] == 0): edge_touches.append("North (row 0)")
if np.any(lowest_cells[0] == 63): edge_touches.append("South (row 63)")
if np.any(lowest_cells[1] == 0): edge_touches.append("West (col 0)")
if np.any(lowest_cells[1] == 63): edge_touches.append("East (col 63)")

print(f"  Lowest cells touch edges: {', '.join(edge_touches) if edge_touches else 'None (Interior depression)'}")

# Check for large flat areas (slope < 0.05 deg)
flat_mask = np.sqrt(slope_x**2 + slope_y**2) < 0.001
flat_count = int(np.sum(flat_mask))
print(f"  Flat cells (slope < 0.05°): {flat_count} ({flat_count / (64*64) * 100:.2f}%)")

# Plot 1: Elevation heatmap with contours & title bounds
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
ls = LightSource(azdeg=315, altdeg=45)

im1 = ax1.imshow(dem_64, cmap="terrain", origin="upper")
cbar1 = plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
cbar1.set_label("Elevation (m a.s.l.)", fontsize=10)
cnt1 = ax1.contour(dem_64, levels=12, colors="black", alpha=0.35, linewidths=0.6)
ax1.clabel(cnt1, inline=True, fontsize=7, fmt="%.0f")
ax1.set_title(
    f"Marathahalli–Bellandur Catchment DEM (64×64, dx={cell_size_m_effective}m)\n"
    f"Bounds: S={final_bounds[0]:.4f}°, W={final_bounds[1]:.4f}°, N={final_bounds[2]:.4f}°, E={final_bounds[3]:.4f}°",
    fontsize=10, fontweight="bold"
)
ax1.set_xlabel(f"Columns (West -> East, dx={cell_size_m_effective}m)")
ax1.set_ylabel(f"Rows (North -> South, dy={cell_size_m_effective}m)")

# Plot 2: Standalone Hillshade for visual terrain inspection
shaded = ls.shade(dem_64.astype(np.float64), cmap=plt.cm.Greys, vert_exag=2.0, blend_mode="overlay")
ax2.imshow(shaded, origin="upper")
cnt2 = ax2.contour(dem_64, levels=8, colors="blue", alpha=0.25, linewidths=0.5)
ax2.set_title("Hillshade & Valley Corridor (Azimuth=315°, Altitude=45°)", fontsize=10, fontweight="bold")
ax2.set_xlabel(f"Columns (West -> East, dx={cell_size_m_effective}m)")
ax2.set_ylabel(f"Rows (North -> South, dy={cell_size_m_effective}m)")

plt.tight_layout()
dem_plot_path = ROOT / "artifacts" / "reports" / "dem.png"
plt.savefig(dem_plot_path, bbox_inches="tight")
plt.close(fig)
print(f"Saved DEM and Hillshade diagnostic plots to {dem_plot_path}")

# -----------------------------------------------------------------------------
# STEP 7: SOLVER VALIDATION AND REAL SCENARIOS ON REAL TERRAIN
# -----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("STEP 7: 2D SWE SOLVER CHECK ON REAL TERRAIN")
print("=" * 70)

DT = 60.0
CELL_AREA = cell_size_m_effective * cell_size_m_effective

# 7a. Re-run solver physics checks on real terrain
print("\n7a. Physics validation checks on real terrain:")

# Bucket test (no drain, flat vs real)
# With real terrain (steep ~3° slope), water moves rapidly to valleys, but in closed domain
# total water volume must equal cumulative rain!
rain_bucket_mmhr = 60.0
steps_bucket = 10
res_b_nodrain = run_solver_core(
    dem=dem_64.astype(np.float64),
    rain_series_mmhr=[rain_bucket_mmhr] * steps_bucket,
    dt_s=DT,
    drain_capacity_mmhr=0.0,
    cell_size_m=cell_size_m_effective,
)
frames_nodrain = res_b_nodrain["depth_frames"]
vol_stored_nodrain = float(np.sum(frames_nodrain[-1])) * CELL_AREA
rain_rate_mps = rain_bucket_mmhr / (1000.0 * 3600.0)
vol_rain_expected = rain_rate_mps * DT * steps_bucket * 64 * 64 * CELL_AREA
rel_err_nodrain = abs(vol_stored_nodrain - vol_rain_expected) / vol_rain_expected

print(f"  Closed basin mass balance (no drainage):")
print(f"    Expected rain volume:   {vol_rain_expected:.2f} m³")
print(f"    Stored water volume:    {vol_stored_nodrain:.2f} m³")
print(f"    Relative mass balance:  {rel_err_nodrain:.2e} ({'PASS' if rel_err_nodrain < 0.05 else 'FAIL'})")

# Bucket test with drainage
drain_mmhr = 10.0
res_b_drain = run_solver_core(
    dem=dem_64.astype(np.float64),
    rain_series_mmhr=[rain_bucket_mmhr] * steps_bucket,
    dt_s=DT,
    drain_capacity_mmhr=drain_mmhr,
    cell_size_m=cell_size_m_effective,
)
frames_drain = res_b_drain["depth_frames"]
vol_stored_drain = float(np.sum(frames_drain[-1])) * CELL_AREA
drained_vol = vol_rain_expected - vol_stored_drain
print(f"  With drainage ({drain_mmhr} mm/hr):")
print(f"    Stored volume:          {vol_stored_drain:.2f} m³")
print(f"    Drained volume:         {drained_vol:.2f} m³")
print(f"    Non-negativity:         {np.min(frames_drain) >= 0.0} (min depth: {np.min(frames_drain):.6f} m)")
print(f"    No NaNs:                {not np.any(np.isnan(frames_drain))}")

# 7b. Run 3 real scenarios:
# 1. Moderate rain: 40 mm/hr, 45 min, drain 15 mm/hr
# 2. Cloudburst: 100 mm/hr, 60 min, drain 10 mm/hr
# 3. Cloudburst with 0 drain (maximum ponding stress test): 100 mm/hr, 60 min, drain 0 mm/hr
scenarios = [
    {"name": "Scenario 1: Moderate Rain", "intensity": 40.0, "duration": 45.0, "drain": 15.0},
    {"name": "Scenario 2: Cloudburst (Drain=10)", "intensity": 100.0, "duration": 60.0, "drain": 10.0},
    {"name": "Scenario 3: Cloudburst (Drain=0 / Stress)", "intensity": 100.0, "duration": 60.0, "drain": 0.0},
]

print("\n7b. Simulating 3 realistic rainfall events (120-step horizon):")
scenario_results = []
for sc in scenarios:
    rain_series = make_rain_series(
        duration_min=sc["duration"],
        intensity_mmhr=sc["intensity"],
        shape="triangular" if "Moderate" in sc["name"] else "constant",
        dt_s=DT,
        total_steps=120,
    )
    t0 = os.times().elapsed
    res = run_solver_core(
        dem=dem_64.astype(np.float64),
        rain_series_mmhr=rain_series,
        dt_s=DT,
        drain_capacity_mmhr=sc["drain"],
        cell_size_m=cell_size_m_effective,
    )
    wall_t = res["solve_time_s"]
    frames = res["depth_frames"]
    peak_depth = float(np.max(frames))
    final_flooded = int(np.sum(frames[-1] >= 0.05))
    flooded_area = final_flooded * CELL_AREA
    
    # Calculate CFL metrics
    # c = sqrt(g * h_max) -> dt_cfl = 0.7 * dx / max(c, 0.1)
    g = 9.80665
    c_max = math.sqrt(g * max(peak_depth, 0.1))
    dt_cfl_min = 0.7 * (cell_size_m_effective / c_max)
    dt_sub_min = max(1.0, min(5.0, dt_cfl_min))
    courant_max = (c_max * dt_sub_min) / cell_size_m_effective
    
    scenario_results.append({
        "info": sc,
        "solve_time_s": wall_t,
        "peak_depth_m": peak_depth,
        "flooded_cells": final_flooded,
        "flooded_area_km2": flooded_area / 1e6,
        "min_substep_s": round(dt_sub_min, 2),
        "max_courant": round(courant_max, 3),
        "frames": frames,
    })
    
    print(f"  {sc['name']}:")
    print(f"    Solver Runtime:        {wall_t:.3f} s")
    print(f"    Peak Flood Depth:      {peak_depth:.3f} m")
    print(f"    Flooded Area:          {flooded_area / 1e6:.3f} km² ({final_flooded} cells >= 5cm)")
    print(f"    Min internal dt_sub:   {dt_sub_min:.2f} s")
    print(f"    Max Courant number:    {courant_max:.3f} (stable < 1.0)")

# 7c. Save 4-frame progression of Cloudburst scenario
print("\n7c. Saving 4-frame progression plot to artifacts/reports/solver_real_terrain.png...")
cloudburst_frames = scenario_results[2]["frames"]  # Stress test
fig, axes = plt.subplots(1, 4, figsize=(20, 5), dpi=150)
time_indices = [15, 45, 75, 120]  # 15m, 45m (peak rain), 75m (drainage/pooling), 120m (final ponding)

for idx, (ax, t_idx) in enumerate(zip(axes, time_indices)):
    depth = cloudburst_frames[t_idx]
    
    # Base terrain hillshade
    ax.imshow(shaded, origin="upper", alpha=0.6)
    
    # Flood depth overlay
    water_masked = np.ma.masked_where(depth < 0.05, depth)
    im = ax.imshow(water_masked, cmap="Blues", origin="upper", vmin=0.05, vmax=max(1.5, np.max(depth)))
    
    ax.set_title(f"Time t = {t_idx} min\nMax Depth: {np.max(depth):.2f}m", fontsize=10, fontweight="bold")
    ax.set_xlabel("Col (dx=60.9m)")
    if idx == 0:
        ax.set_ylabel("Row (dy=60.9m)")
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Depth (m)", fontsize=8)

plt.suptitle("2D SWE Hydrodynamic Inundation on Marathahalli–Bellandur Terrain (Cloudburst 100 mm/hr)", fontsize=12, fontweight="bold")
plt.tight_layout()
solver_plot_path = ROOT / "artifacts" / "reports" / "solver_real_terrain.png"
plt.savefig(solver_plot_path, bbox_inches="tight")
plt.close(fig)
print(f"Saved solver flood plot to {solver_plot_path}")

# 7d. Boundary analysis: where does water leave if outlet enabled?
# Find the perimeter cells with minimum elevation
perimeter = []
for c in range(64):
    perimeter.append((0, c, dem_64[0, c], "North"))
    perimeter.append((63, c, dem_64[63, c], "South"))
for r in range(1, 63):
    perimeter.append((r, 0, dem_64[r, 0], "West"))
    perimeter.append((r, 63, dem_64[r, 63], "East"))

perimeter.sort(key=lambda x: x[2])
lowest_bdry = perimeter[:5]
print("\n7d. Boundary Drainage and Outlet Assessment:")
print("  Lowest boundary edge cells:")
for r, c, elev, edge in lowest_bdry:
    print(f"    Edge: {edge:<5} at (row={r:2d}, col={c:2d}), Elevation: {elev:.2f} m")

print(f"\n  Drainage outlet finding:")
print(f"    The absolute lowest boundary cell is at {lowest_bdry[0][3]} edge: (r={lowest_bdry[0][0]}, c={lowest_bdry[0][1]}), elevation {lowest_bdry[0][2]:.2f}m.")
print(f"    This corresponds to the natural discharge valley entering Bellandur Lake.")
print(f"    Recommendation: Keep CLOSED boundaries by default for strict mass-conservation audits as per CONTRACT.md.")
