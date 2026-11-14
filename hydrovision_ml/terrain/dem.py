"""Digital Elevation Model (DEM) ingestion and synthetic topography generator.

Phase: Phase 1 (Terrain & Preprocessing)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


def make_synthetic_dem(
    rows: int = 64,
    cols: int = 64,
    cell_size_m: float = 40.0,
) -> np.ndarray:
    """Generate a synthetic digital elevation model with gentle slope and retention bowls.

    Parameters
    ----------
    rows : int
        Number of grid rows (default: 64).
    cols : int
        Number of grid columns (default: 64).
    cell_size_m : float
        Grid cell spatial resolution in meters (default: 40.0).

    Returns
    -------
    np.ndarray
        Elevation array of shape (rows, cols) in meters above sea level.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 1.
    """
    raise NotImplementedError("Planned for Phase 1: Terrain ingestion and DEM processing.")


def load_real_dem(
    filepath: str,
    target_rows: int = 64,
    target_cols: int = 64,
) -> np.ndarray:
    """Load a real GeoTIFF DEM file, reproject to local UTM, crop, and resample to target grid.

    Parameters
    ----------
    filepath : str
        Path to input GeoTIFF file.
    target_rows : int
        Target grid row resolution (default: 64).
    target_cols : int
        Target grid column resolution (default: 64).

    Returns
    -------
    np.ndarray
        Resampled 2D elevation array of shape (target_rows, target_cols) in meters.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 1.
    """
    raise NotImplementedError("Planned for Phase 1: Terrain ingestion and DEM processing.")


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

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 1.
    """
    raise NotImplementedError("Planned for Phase 1: Terrain ingestion and DEM processing.")


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

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 1.
    """
    raise NotImplementedError("Planned for Phase 1: Terrain ingestion and DEM processing.")

