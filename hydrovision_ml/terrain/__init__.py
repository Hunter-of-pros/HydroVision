"""Terrain processing subpackage for HydroVision.

Handles DEM ingestion, reprojection, slope derivation, and synthetic topography.
"""

from hydrovision_ml.terrain.dem import (
    dem_quality_check,
    load_real_dem,
    make_synthetic_dem,
    plot_dem,
)

__all__ = ["make_synthetic_dem", "load_real_dem", "plot_dem", "dem_quality_check"]

