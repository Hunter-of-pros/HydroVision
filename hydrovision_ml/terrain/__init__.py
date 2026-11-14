"""Terrain processing subpackage for HydroVision.

Handles DEM ingestion, reprojection, slope derivation, and synthetic topography.
Phase: Phase 1 (Terrain & Preprocessing)
"""

from hydrovision_ml.terrain.dem import (
    compute_slopes,
    dem_quality_check,
    load_real_dem,
    load_terrain,
    make_synthetic_dem,
    plot_dem,
    save_terrain,
)

__all__ = [
    "make_synthetic_dem",
    "compute_slopes",
    "load_real_dem",
    "dem_quality_check",
    "save_terrain",
    "load_terrain",
    "plot_dem",
]
