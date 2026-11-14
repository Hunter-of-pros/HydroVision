# Digital Elevation Model (DEM) Preparation Guide

This guide details how to acquire, preprocess, and condition digital elevation data for HydroVision.

---

## 1. Topographic Data Sources
- **Copernicus GLO-30**: Global 30-meter elevation model (recommended for urban areas outside the US).
- **USGS 3D Elevation Program (3DEP)**: High-resolution (1m to 10m) lidar-derived DEMs for US municipalities.
- **OpenTopography**: API access to high-resolution point clouds and bare-earth terrain models.
- **Synthetic Generator**: Built-in `hydrovision_ml.terrain.make_synthetic_dem` for offline testing.

---

## 2. Spatial Extent & Grid Definition
- **Catchment Area**: $2.56\text{ km} \times 2.56\text{ km}$ ($64 \times 64$ cells at $40.0\text{ m}$ spacing).
- **Coordinate Reference System (CRS)**: Must be reprojected to a local Universal Transverse Mercator (UTM) zone with meter units (e.g., EPSG:32643 for Bangalore, India) prior to rasterization.
- **Orientation**: Array index [0, 0] must correspond to North-West corner.

---

## 3. Preprocessing with Rasterio & GDAL

### Step 3.1: Reproject and Crop with GDAL
```bash
# Reproject source WGS84 GeoTIFF to local UTM (EPSG:32643 for Bangalore) and crop to 2.56 km square
gdalwarp -t_srs EPSG:32643 \
  -te 777000 1428000 779560 1430560 \
  -tr 40.0 40.0 \
  -r bilinear \
  raw_dem_wgs84.tif cropped_utm_40m.tif

# Verify dimensions are exactly 64 x 64
gdalinfo cropped_utm_40m.tif | grep "Size is"
# Output should report: Size is 64, 64
```

### Step 3.2: Export to `terrain.npz` with Python & Rasterio
```python
import rasterio
import numpy as np

with rasterio.open("cropped_utm_40m.tif") as src:
    elevation = src.read(1).astype(np.float64)
    # Replace NoData values with minimum valid elevation
    elevation[elevation == src.nodata] = np.nanmin(elevation)
    bounds = list(src.bounds) # [minx, miny, maxx, maxy]

# Calculate second-order central spatial slopes
slope_y, slope_x = np.gradient(elevation, 40.0)

np.savez_compressed(
    "artifacts/data/terrain.npz",
    elevation=elevation,
    slope_x=slope_x,
    slope_y=slope_y,
    bounds=bounds,
)
print(f"Exported terrain.npz: shape={elevation.shape}, elev=[{elevation.min():.1f}m, {elevation.max():.1f}m]")
```

---

## 4. Hydrological Conditioning & Sink Handling
- Identification of natural depressions vs. digital elevation artifacts.
- Evaluating sink-filling algorithms vs. depression storage preservation.
- Verifying overland flow connectivity from North-West uplands to South-East drainage outlets.

---

## 5. Exporting to `artifacts/data/terrain.npz`
- Saving NumPy archive with keys:
  - `elevation`: 2D float64 array of shape $(64, 64)$
  - `slope_x`: finite difference gradient $\partial z / \partial x$
  - `slope_y`: finite difference gradient $\partial z / \partial y$
  - `bounds`: `[min_lat, min_lon, max_lat, max_lon]`
- Performing automated QA checks with `hydrovision_ml.terrain.dem_quality_check()`.

