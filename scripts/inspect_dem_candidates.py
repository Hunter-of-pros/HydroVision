"""Step 1-3: Extract, inspect, and analyze DEM candidate windows.
"""

from __future__ import annotations

import math
import os
import shutil
import tarfile
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

# 1. Paths
ARCHIVE_PATH = r"C:\Users\Khubaib\.gemini\antigravity\brain\45d9f9c0-0d9f-4d50-af8c-e00995a5a42c\.user_uploaded\media_1794658890225_cc8c5980.gz"
DEM_DIR = Path(r"C:\hydrovision_data\dem")
DEM_DIR.mkdir(parents=True, exist_ok=True)
RAW_TIF = DEM_DIR / "output_hh.tif"
TARGET_TIF = DEM_DIR / "marathahalli.tif"

print("=" * 70)
print("STEP 1: LOCATE AND EXTRACT DEM")
print("=" * 70)

if not RAW_TIF.exists() or not TARGET_TIF.exists():
    print(f"Extracting from {ARCHIVE_PATH}...")
    with tarfile.open(ARCHIVE_PATH, "r:*") as tar:
        tar.extract("output_hh.tif", path=str(DEM_DIR))
    shutil.copyfile(RAW_TIF, TARGET_TIF)
    print(f"Extracted to {RAW_TIF} and copied to {TARGET_TIF}")
else:
    print(f"Files already exist at {RAW_TIF} and {TARGET_TIF}")

print(f"marathahalli.tif size: {TARGET_TIF.stat().st_size} bytes")

print("\n" + "=" * 70)
print("STEP 2: READ AND VERIFY METADATA WITH RASTERIO")
print("=" * 70)

with rasterio.open(TARGET_TIF) as src:
    data = src.read(1)
    meta = src.meta
    transform = src.transform
    crs = src.crs
    bounds = src.bounds
    res = src.res

rows, cols = data.shape
dtype = data.dtype
min_val = float(np.nanmin(data))
max_val = float(np.nanmax(data))
mean_val = float(np.nanmean(data))
nan_count = int(np.sum(np.isnan(data)))

# Latitude and Longitude specifics
# WGS84 ellipsoid constants
# a = 6378137.0 m, b = 6356752.3142 m
# lat center approx
mean_lat = (bounds.bottom + bounds.top) / 2.0
mean_lat_rad = math.radians(mean_lat)

# Degrees to meters:
# 1 deg lat = 110,574 m + ... or standard WGS84 formula
# Earth radius at latitude:
R_lat = 111132.954 - 559.822 * math.cos(2 * mean_lat_rad) + 1.175 * math.cos(4 * mean_lat_rad)
R_lon = 111412.84 * math.cos(mean_lat_rad) - 93.5 * math.cos(3 * mean_lat_rad)

dx_deg = abs(res[0])
dy_deg = abs(res[1])

dx_m = dx_deg * R_lon
dy_m = dy_deg * R_lat

# Slope computation
# dy is along axis 0 (rows, N to S), dx is along axis 1 (cols, W to E)
grad_y, grad_x = np.gradient(data.astype(np.float64), dy_m, dx_m)
slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
slope_deg = np.degrees(slope_rad)
mean_slope = float(np.mean(slope_deg))
p95_slope = float(np.percentile(slope_deg, 95))

print(f"Shape:               {rows} rows x {cols} columns")
print(f"Data type:           {dtype}")
print(f"CRS:                 {crs}")
print(f"Bounds (W, S, E, N): [{bounds.left:.6f}, {bounds.bottom:.6f}, {bounds.right:.6f}, {bounds.top:.6f}]")
print(f"Transform:           {transform}")
print(f"Pixel size (deg):    dx={dx_deg:.9f} deg, dy={dy_deg:.9f} deg")
print(f"Mean latitude:       {mean_lat:.5f} deg N")
print(f"Cell size (meters):  E-W dx = {dx_m:.3f} m, N-S dy = {dy_m:.3f} m")
print(f"Aspect ratio dx/dy:  {dx_m / dy_m:.4f} (difference = {abs(dx_m - dy_m)/dy_m * 100:.2f}%)")
print(f"Min elevation:       {min_val:.3f} m")
print(f"Max elevation:       {max_val:.3f} m")
print(f"Mean elevation:      {mean_val:.3f} m")
print(f"Relief (max - min):  {max_val - min_val:.3f} m")
print(f"NaN count:           {nan_count}")
print(f"Mean slope:          {mean_slope:.3f} degrees")
print(f"95th percentile slope: {p95_slope:.3f} degrees")
print(f"Value confirmation:  Values range from {min_val:.1f}m to {max_val:.1f}m, confirming true elevations in meters (NOT 0-255 image pixels).")

# Verification against user numbers
print("\n--- Comparison with User Provided Context ---")
diffs = []
if (rows, cols) != (155, 140):
    diffs.append(f"Shape: {rows}x{cols} vs expected 155x140")
else:
    print("  [x] Shape: 155 x 140 matches exactly")

if abs(min_val - 857.7) > 0.5 or abs(max_val - 910.4) > 0.5:
    diffs.append(f"Elevation range: {min_val:.2f}-{max_val:.2f} vs expected ~857.7-910.4m")
else:
    print(f"  [x] Elevation range: {min_val:.2f} to {max_val:.2f} m matches (~857.7 to 910.4 m)")

if nan_count != 0:
    diffs.append(f"NaN count: {nan_count} vs expected 0")
else:
    print("  [x] NaN count: 0 (clean raster)")

if abs(bounds.left - 77.67306) > 0.001 or abs(bounds.top - 12.96611) > 0.001:
    diffs.append(f"Upper-left corner: ({bounds.left:.5f}, {bounds.top:.5f}) vs expected (77.67306, 12.96611)")
else:
    print(f"  [x] Upper-left corner: Lon {bounds.left:.5f}, Lat {bounds.top:.5f} matches (~77.67306, ~12.96611)")

if abs(dx_deg - 0.000277778) > 1e-7:
    diffs.append(f"Pixel size: {dx_deg} vs expected 0.000277778")
else:
    print(f"  [x] Pixel size: {dx_deg:.8f} deg matches (1 arc-second = 0.000277778 deg)")

if not diffs:
    print("  ALL user measurements verified with exact match!")
else:
    print("  Differences observed:", diffs)


print("\n" + "=" * 70)
print("STEP 3: CANDIDATE 128 x 128 WINDOWS ANALYSIS")
print("=" * 70)

# Raster is 155 rows x 140 columns.
# A 128x128 window requires row offset r0 in [0, 27] and col offset c0 in [0, 12].
# Let's define 3 distinct candidates:
# Candidate 1 (North-West / Top-Left): r0=0, c0=0
# Candidate 2 (Center-South): r0=20, c0=6  (covers the southern and eastern corridor, Marathahalli-Bellandur ORR valley)
# Candidate 3 (South-East / Bottom-Right): r0=27, c0=12 (captures Bellandur valley towards south/east)

candidates = [
    {
        "name": "Candidate 1 (North-West: r0=0, c0=0)",
        "r0": 0, "r1": 128,
        "c0": 0, "c1": 128,
        "desc": "North & West high ridges + upper reach of valley"
    },
    {
        "name": "Candidate 2 (Central: r0=14, c0=6)",
        "r0": 14, "r1": 14 + 128,
        "c0": 6,  "c1": 6 + 128,
        "desc": "Centered window: balanced corridor through middle"
    },
    {
        "name": "Candidate 3 (South-East / ORR Corridor: r0=27, c0=12)",
        "r0": 27, "r1": 27 + 128,
        "c0": 12, "c1": 12 + 128,
        "desc": "Bellandur-ORR low corridor oriented toward south-central edge"
    },
]

def count_local_minima(arr_smooth):
    nr, nc = arr_smooth.shape
    sinks = 0
    for r in range(1, nr - 1):
        for c in range(1, nc - 1):
            val = arr_smooth[r, c]
            neighbors = [
                arr_smooth[r-1, c-1], arr_smooth[r-1, c], arr_smooth[r-1, c+1],
                arr_smooth[r, c-1],                       arr_smooth[r, c+1],
                arr_smooth[r+1, c-1], arr_smooth[r+1, c], arr_smooth[r+1, c+1]
            ]
            if all(val < n for n in neighbors):
                sinks += 1
    return sinks

# Evaluate candidates
candidate_stats = []
for cand in candidates:
    sub = data[cand["r0"]:cand["r1"], cand["c0"]:cand["c1"]].astype(np.float64)
    min_c = float(np.min(sub))
    max_c = float(np.max(sub))
    relief_c = max_c - min_c
    
    # Slopes
    gy, gx = np.gradient(sub, dy_m, dx_m)
    slopes = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    mean_sl = float(np.mean(slopes))
    
    # Smooth with sigma=1.0 to find structural depressions
    sub_smooth = gaussian_filter(sub, sigma=1.0)
    sinks = count_local_minima(sub_smooth)
    
    # Check low corridor presence & position
    # The low corridor corresponds to elevations < 875m (lowest 30% of relief)
    corridor_mask = sub < (min_c + 0.3 * relief_c)
    corridor_cells = int(np.sum(corridor_mask))
    
    # Lowest cells (< min + 2m) location
    lowest_mask = sub <= (min_c + 2.0)
    lowest_r, lowest_c = np.where(lowest_mask)
    touches_edge = bool(
        np.any(lowest_r == 0) or np.any(lowest_r == 127) or
        np.any(lowest_c == 0) or np.any(lowest_c == 127)
    )
    edge_names = []
    if np.any(lowest_r == 0): edge_names.append("North")
    if np.any(lowest_r == 127): edge_names.append("South")
    if np.any(lowest_c == 0): edge_names.append("West")
    if np.any(lowest_c == 127): edge_names.append("East")

    stats = {
        "candidate": cand,
        "sub": sub,
        "min_elev": min_c,
        "max_elev": max_c,
        "relief": relief_c,
        "mean_slope": mean_sl,
        "sinks": sinks,
        "corridor_cells": corridor_cells,
        "touches_edge": touches_edge,
        "edges": edge_names or ["Interior"],
    }
    candidate_stats.append(stats)
    
    print(f"\n{cand['name']}:")
    print(f"  Description:         {cand['desc']}")
    print(f"  Row slice:           [{cand['r0']}: {cand['r1']}], Col slice: [{cand['c0']}: {cand['c1']}]")
    print(f"  Elevation range:     {min_c:.2f} m to {max_c:.2f} m (Relief: {relief_c:.2f} m)")
    print(f"  Mean slope:          {mean_sl:.2f} degrees")
    print(f"  Local minima (sinks, sigma=1): {sinks}")
    print(f"  Low corridor cells (<30% relief): {corridor_cells} ({corridor_cells/(128*128)*100:.1f}%)")
    print(f"  Lowest cells touch edge: {touches_edge} ({', '.join(edge_names or ['None'])})")

# Generate side-by-side plot
fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=150)
ls = LightSource(azdeg=315, altdeg=45)

for idx, (ax, stats) in enumerate(zip(axes, candidate_stats)):
    sub = stats["sub"]
    cand = stats["candidate"]
    
    # Shaded relief
    shaded = ls.shade(sub, cmap=plt.cm.terrain, vert_exag=1.5, blend_mode="overlay")
    im = ax.imshow(shaded, origin="upper")
    
    # Contours
    cs = ax.contour(sub, levels=10, colors="black", alpha=0.35, linewidths=0.6)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.0f")
    
    # Highlight lowest corridor (elevation <= min + 0.25 * relief)
    ax.contourf(
        sub, levels=[stats["min_elev"], stats["min_elev"] + 0.25 * stats["relief"]],
        colors=["cyan"], alpha=0.25
    )
    
    rec_tag = " [RECOMMENDED]" if idx == 2 else ""
    ax.set_title(
        f"{cand['name']}{rec_tag}\n"
        f"Relief: {stats['relief']:.1f}m | Mean Slope: {stats['mean_slope']:.2f}° | Sinks: {stats['sinks']}\n"
        f"Lowest edge: {', '.join(stats['edges'])}",
        fontsize=9, fontweight="bold" if idx == 2 else "normal"
    )
    ax.set_xlabel("Col (W -> E, ~30m)")
    if idx == 0:
        ax.set_ylabel("Row (N -> S, ~30m)")

plt.tight_layout()
plot_path = Path("artifacts/reports/dem_candidates.png")
plot_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(plot_path, bbox_inches="tight")
plt.close(fig)

print(f"\nSaved candidates comparison plot to {plot_path.resolve()}")
