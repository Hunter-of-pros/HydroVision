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
- Reprojecting source GeoTIFF to local UTM:
  ```bash
  # TODO: add GDAL warp command line example
  ```
- Resampling to target $64 \times 64$ shape using bilinear or cubic spline interpolation.
- Handling and replacing NoData pixels using nearest-neighbor interpolation.

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

