# Digital Elevation Model (DEM) Preparation Guide — Real Terrain Pipeline

This guide documents the exact steps used to extract, verify, condition, and downsample the real-world digital elevation model for the Marathahalli–Bellandur Outer Ring Road (ORR) catchment in East Bengaluru.

---

## 1. Raw Dataset Provenance & Attribution

- **Source File**: `output_hh.tif` (extracted from `rasters_COP30.tar.gz`)
- **Origin**: Copernicus GLO-30 Digital Elevation Model accessed via OpenTopography
- **Attribution & Licence**:
  > Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
- **Raw Properties**:
  - Dimensions: 155 rows × 140 columns
  - Data Type: `float32` (elevations in meters a.s.l.)
  - Coordinate Reference System: `EPSG:4326` (WGS 84 geographic coordinates)
  - Native Resolution: 1 arc-second ($\approx 0.000277778^\circ$)
  - Native Cell Size: E-W $dx \approx 30.14\text{ m}$, N-S $dy \approx 30.73\text{ m}$ (mean latitude $12.945^\circ\text{ N}$)
  - Bounds: Lon $77.672917^\circ\text{ E}$ to $77.711806^\circ\text{ E}$, Lat $12.923194^\circ\text{ N}$ to $12.966250^\circ\text{ N}$
  - Elevation Range: $857.75\text{ m}$ to $910.38\text{ m}$ (Relief: $52.63\text{ m}$), NaN count: 0

---

## 2. Ingestion & Storage Rules

1. The raw GeoTIFF is extracted outside OneDrive to avoid cloud sync lock issues:
   `C:/hydrovision_data/dem/marathahalli.tif`
2. **Git Policy**: `*.tif`, `*.tiff`, `*.tar.gz`, and `*.gz` are strictly added to `.gitignore`. Raw raster binaries are never committed to Git. Only the conditioned derivative `artifacts/data/terrain.npz` is tracked.

---

## 3. Window Selection: Candidate 3 (ORR Corridor)

From the 155 × 140 native raster, three 128 × 128 candidate windows were evaluated. **Candidate 3** was selected:
- **Slice**: `rows [27:155], cols [12:140]`
- **Geographic Extent**:
  - South: $12.923194^\circ\text{ N}$
  - West: $77.676250^\circ\text{ E}$
  - North: $12.958750^\circ\text{ N}$
  - East: $77.711806^\circ\text{ E}$
- **Why Candidate 3**:
  1. Captures the high northern ridge in Marathahalli (~909m) down into the Bellandur lake basin in the south (~857m).
  2. Centers the Outer Ring Road flood-prone transit corridor.
  3. Lowest boundary drainage sits on the eastern/southern edge, avoiding unnatural central lake retention.
  4. Lowest structural depression count (162 raw sinks vs 172 in NW window).

---

## 4. Downsampling & Hydrological Conditioning

To match CONTRACT.md's canonical $64 \times 64$ grid:
1. **2× Block Mean Downsampling** (NOT nearest neighbor):
   ```python
   dem_64_raw = native_128.reshape(64, 2, 64, 2).mean(axis=(1, 3))
   ```
2. **Light Gaussian Smoothing** ($\sigma = 0.8$):
   Filters out 30m high-frequency DSM noise (individual commercial buildings and tree canopies) while preserving true catchment-scale ridges and drainage corridors.
3. **Effective Cell Size**:
   - E-W cell size $dx = 60.283\text{ m}$
   - N-S cell size $dy = 61.461\text{ m}$
   - Mean effective resolution: **$60.9\text{ m}$** (aspect ratio difference: $1.92\% < 3\%$).
   - Total Catchment Size: $3.86\text{ km} \times 3.93\text{ km} \approx 15.18\text{ km}^2$.

---

## 5. Artifact Packaging (`artifacts/data/terrain.npz`)

Exported with `numpy.savez_compressed` containing:
- `dem_m`: 2D `float32` array $(64, 64)$
- `elevation`: 2D `float64` array $(64, 64)$
- `slope_x`: East-West finite-difference slope $\partial z / \partial x$
- `slope_y`: North-South finite-difference slope $\partial z / \partial y$
- `bounds`: `[12.923194, 77.676250, 12.958750, 77.711806]` $[S, W, N, E]$
- `cell_size_m`: $60.9$
- `dx_m`: $60.9$
- `is_synthetic`: `False`
- `smoothing_sigma`: $0.8$
- `window_used`: `[27, 155, 12, 140]`
- `source`: Official Copernicus citation string

---

## 6. Diagnostic Outputs

- `artifacts/reports/dem_candidates.png`: 3-way candidate comparison.
- `artifacts/reports/dem.png`: High-resolution elevation heatmap with contours + standalone hillshade.
- `artifacts/reports/solver_real_terrain.png`: 4-frame 2D SWE inundation simulation under a 100 mm/hr cloudburst.
