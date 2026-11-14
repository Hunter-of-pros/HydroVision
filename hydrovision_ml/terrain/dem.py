"""Digital Elevation Model (DEM) ingestion and synthetic topography generator.

Phase: Phase 1 (Terrain & Preprocessing)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from hydrovision_ml.config import (
    CELL_SIZE_M,
    COLS,
    ROWS,
)


def make_synthetic_dem(
    rows: int = ROWS,
    cols: int = COLS,
    cell_size_m: float = CELL_SIZE_M,
    seed: int = 42,
) -> np.ndarray:
    """Generate a realistic synthetic DEM with regional slope, retention basins, and micro-relief.

    Parameters
    ----------
    rows : int
        Number of grid rows (default: 64).
    cols : int
        Number of grid columns (default: 64).
    cell_size_m : float
        Grid cell spatial resolution in meters (default: 40.0).
    seed : int
        Random seed for micro-relief reproducibility.

    Returns
    -------
    np.ndarray
        Elevation array of shape (rows, cols) in meters above sea level (float64).
    """
    r_idx, c_idx = np.indices((rows, cols))

    # Regional slope: NW (row 0, col 0) at ~100m down to SE (row rows-1, col cols-1) at ~81m
    regional_slope = 100.0 - 0.15 * (r_idx + c_idx)

    # Primary retention bowl in SE sector (centered near (42, 42))
    dist1_sq = (r_idx - 42) ** 2 + (c_idx - 42) ** 2
    bowl1 = 4.5 * np.exp(-dist1_sq / (2.0 * (6.0 ** 2)))

    # Secondary depression in East sector (centered near (20, 48))
    dist2_sq = (r_idx - 20) ** 2 + (c_idx - 48) ** 2
    bowl2 = 3.2 * np.exp(-dist2_sq / (2.0 * (5.0 ** 2)))

    # Smooth harmonic micro-relief for natural drainage channel patterns
    rng = np.random.default_rng(seed)
    micro_relief = (
        0.4 * np.sin(2.0 * np.pi * r_idx / 24.0) * np.cos(2.0 * np.pi * c_idx / 24.0)
        + 0.2 * np.sin(2.0 * np.pi * (r_idx + c_idx) / 16.0)
    )

    dem = regional_slope - bowl1 - bowl2 + micro_relief
    return np.round(dem, 3).astype(np.float64)


def compute_slopes(
    dem: np.ndarray,
    cell_size_m: float = CELL_SIZE_M,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate finite-difference spatial elevation slopes (dz/dx, dz/dy).

    Uses second-order central differences in the interior and first-order
    one-sided differences on grid boundaries.

    Parameters
    ----------
    dem : np.ndarray
        2D elevation grid of shape (rows, cols).
    cell_size_m : float
        Cell resolution in meters.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (slope_x, slope_y) arrays matching dem shape:
        - slope_x = dz / dx (along columns, axis 1, East-West)
        - slope_y = dz / dy (along rows, axis 0, North-South)
    """
    dem_arr = np.asarray(dem, dtype=np.float64)
    # np.gradient returns [d/d_axis0, d/d_axis1]
    grad_y, grad_x = np.gradient(dem_arr, cell_size_m)
    return np.round(grad_x, 6), np.round(grad_y, 6)


def load_real_dem(
    filepath: str,
    target_rows: int = ROWS,
    target_cols: int = COLS,
) -> np.ndarray:
    """Load a real DEM file, reproject/resample to target grid dimensions.

    Supports GeoTIFF (.tif, .tiff), NumPy (.npy, .npz), and CSV formats.

    Parameters
    ----------
    filepath : str
        Path to input DEM file.
    target_rows : int
        Target grid row resolution (default: 64).
    target_cols : int
        Target grid column resolution (default: 64).

    Returns
    -------
    np.ndarray
        Resampled 2D elevation array of shape (target_rows, target_cols) in meters.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"DEM file not found: {filepath}")

    suffix = path.suffix.lower()

    if suffix in [".npy"]:
        data = np.load(path)
    elif suffix in [".npz"]:
        archive = np.load(path)
        if "elevation" in archive:
            data = archive["elevation"]
        elif "dem" in archive:
            data = archive["dem"]
        else:
            first_key = archive.files[0]
            data = archive[first_key]
    elif suffix in [".tif", ".tiff"]:
        try:
            import rasterio
            from rasterio.enums import Resampling

            with rasterio.open(path) as src:
                data = src.read(
                    1,
                    out_shape=(target_rows, target_cols),
                    resampling=Resampling.bilinear,
                )
                nodata = src.nodata
                if nodata is not None:
                    mask = data == nodata
                    if np.any(mask):
                        valid_mean = float(np.nanmean(data[~mask]))
                        data[mask] = valid_mean
        except ImportError:
            raise ImportError(
                "rasterio is required to load GeoTIFF DEMs. "
                "Install with `pip install rasterio` or use .npy/.npz format."
            )
    elif suffix in [".csv", ".txt"]:
        data = np.loadtxt(path, delimiter=",")
    else:
        raise ValueError(f"Unsupported DEM file extension '{suffix}'. Use .tif, .npy, or .npz.")

    data = np.asarray(data, dtype=np.float64)

    # Resample if dimensions do not match
    if data.shape != (target_rows, target_cols):
        r_orig = np.linspace(0, 1, data.shape[0])
        c_orig = np.linspace(0, 1, data.shape[1])
        r_target = np.linspace(0, 1, target_rows)
        c_target = np.linspace(0, 1, target_cols)

        # Bilinear interpolation via scipy or numpy grid
        try:
            from scipy.interpolate import RegularGridInterpolator

            interp = RegularGridInterpolator((r_orig, c_orig), data, method="linear")
            grid_r, grid_c = np.meshgrid(r_target, c_target, indexing="ij")
            data = interp((grid_r, grid_c))
        except ImportError:
            # Fallback 1D interpolation along both axes
            temp = np.zeros((target_rows, data.shape[1]), dtype=np.float64)
            for j in range(data.shape[1]):
                temp[:, j] = np.interp(r_target, r_orig, data[:, j])
            resampled = np.zeros((target_rows, target_cols), dtype=np.float64)
            for i in range(target_rows):
                resampled[i, :] = np.interp(c_target, c_orig, temp[i, :])
            data = resampled

    return np.round(data, 3)


def dem_quality_check(dem: np.ndarray) -> Dict[str, Any]:
    """Perform hydrological QA on DEM: check for NaNs, sinks, extreme gradients, and bounds.

    Parameters
    ----------
    dem : np.ndarray
        2D elevation grid.

    Returns
    -------
    dict
        Quality diagnostics including min/max elevation, slope stats, and sink count.
    """
    arr = np.asarray(dem, dtype=np.float64)
    nan_count = int(np.sum(np.isnan(arr)))
    inf_count = int(np.sum(np.isinf(arr)))

    valid_arr = arr[np.isfinite(arr)]
    if len(valid_arr) == 0:
        return {
            "is_valid": False,
            "nan_count": nan_count,
            "inf_count": inf_count,
            "error": "Array contains no finite values",
        }

    min_elev = float(np.min(valid_arr))
    max_elev = float(np.max(valid_arr))
    mean_elev = float(np.mean(valid_arr))
    std_elev = float(np.std(valid_arr))

    # Slope stats
    grad_x, grad_y = compute_slopes(arr)
    slope_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
    mean_slope = float(np.mean(slope_mag))
    max_slope = float(np.max(slope_mag))

    # Count depression sinks (cells lower than all 8 neighbors in interior)
    sinks = 0
    rows, cols = arr.shape
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            val = arr[r, c]
            neighbors = [
                arr[r - 1, c - 1],
                arr[r - 1, c],
                arr[r - 1, c + 1],
                arr[r, c - 1],
                arr[r, c + 1],
                arr[r + 1, c - 1],
                arr[r + 1, c],
                arr[r + 1, c + 1],
            ]
            if all(val < n for n in neighbors):
                sinks += 1

    return {
        "is_valid": bool(nan_count == 0 and inf_count == 0 and min_elev >= 0.0),
        "shape": list(arr.shape),
        "nan_count": nan_count,
        "inf_count": inf_count,
        "min_elevation": round(min_elev, 3),
        "max_elevation": round(max_elev, 3),
        "mean_elevation": round(mean_elev, 3),
        "std_elevation": round(std_elev, 3),
        "mean_slope": round(mean_slope, 5),
        "max_slope": round(max_slope, 5),
        "sink_count": sinks,
    }


def save_terrain(
    dem: np.ndarray,
    output_path: str = "artifacts/data/terrain.npz",
    bounds: Optional[List[float]] = None,
    cell_size_m: float = CELL_SIZE_M,
) -> Path:
    """Export DEM elevation and finite-difference slopes to a compressed .npz archive.

    Parameters
    ----------
    dem : np.ndarray
        2D elevation grid of shape (rows, cols).
    output_path : str
        Destination path.
    bounds : Optional[list[float]]
        Geographic bounds [min_lat, min_lon, max_lat, max_lon].
    cell_size_m : float
        Cell resolution in meters.

    Returns
    -------
    Path
        Path to saved .npz archive.
    """
    if bounds is None:
        bounds = [12.920, 77.560, 12.943, 77.583]

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    slope_x, slope_y = compute_slopes(dem, cell_size_m=cell_size_m)
    np.savez_compressed(
        out_file,
        elevation=dem.astype(np.float64),
        slope_x=slope_x.astype(np.float64),
        slope_y=slope_y.astype(np.float64),
        bounds=np.array(bounds, dtype=np.float64),
        dx_m=np.float64(cell_size_m),
    )
    return out_file


def load_terrain(input_path: str = "artifacts/data/terrain.npz") -> Dict[str, Any]:
    """Load terrain archive and return dictionary conforming to CONTRACT.md get_terrain().

    Parameters
    ----------
    input_path : str
        Path to terrain.npz archive.

    Returns
    -------
    dict
        Terrain dictionary:
        - elevation : list[list[float]]
        - dx_m : float
        - bounds : list[float]
        - shape : list[int]
        - min_elevation : float
        - max_elevation : float
    """
    path = Path(input_path)
    if not path.is_file():
        # Fallback to generating synthetic DEM if archive does not exist yet
        dem = make_synthetic_dem()
        bounds = [12.920, 77.560, 12.943, 77.583]
        dx_m = float(CELL_SIZE_M)
    else:
        archive = np.load(path)
        dem = archive["elevation"]
        bounds = archive["bounds"].tolist()
        dx_m = float(archive["dx_m"]) if "dx_m" in archive else float(CELL_SIZE_M)

    return {
        "elevation": dem.tolist(),
        "dx_m": dx_m,
        "bounds": bounds,
        "shape": list(dem.shape),
        "min_elevation": round(float(np.min(dem)), 2),
        "max_elevation": round(float(np.max(dem)), 2),
    }


def plot_dem(
    dem: np.ndarray,
    output_path: Optional[str] = None,
) -> None:
    """Render a shaded relief map with contour overlay of the DEM.

    Parameters
    ----------
    dem : np.ndarray
        2D elevation grid of shape (rows, cols).
    output_path : Optional[str]
        If provided, save the figure to this file path; otherwise display interactively.
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LightSource

        fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
        ls = LightSource(azdeg=315, altdeg=45)
        shaded = ls.shade(dem, cmap=plt.cm.terrain, vert_exag=0.5, blend_mode="overlay")

        im = ax.imshow(shaded, origin="upper")
        contours = ax.contour(dem, levels=12, colors="black", alpha=0.3, linewidths=0.6)
        ax.clabel(contours, inline=True, fontsize=7)
        ax.set_title("HydroVision Catchment Topography (DEM)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Col index (West -> East, dx=40m)")
        ax.set_ylabel("Row index (North -> South, dy=40m)")

        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(out_p, bbox_inches="tight")
            plt.close(fig)
        else:
            plt.close(fig)
    except ImportError:
        pass
