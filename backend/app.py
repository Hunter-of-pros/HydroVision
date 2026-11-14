"""FastAPI web server skeleton for HydroVision.

Owner: Backend (Vikas)
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend import schemas, services

app = FastAPI(
    title="HydroVision API",
    description="Physics-informed neural surrogate backend for real-time urban flood forecasting.",
    version="1.0.0",
)

# Enable GZip compression for high-dimensional depth frame payloads
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Allow Cross-Origin Resource Sharing (CORS) from Vite development server
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=schemas.HealthResponse,
    summary="Health and model runtime status",
    tags=["System"],
)
def get_health() -> Dict[str, Any]:
    """Return operational health status, mock mode indicator, and contract version."""
    return services.get_health()


@app.get(
    "/config",
    response_model=schemas.ConfigResponse,
    summary="Simulation configuration and parameter boundaries",
    tags=["Configuration"],
)
def get_config() -> Dict[str, Any]:
    """Return grid dimensions, temporal horizons, and valid parameter ranges."""
    return services.get_config()


@app.get(
    "/terrain",
    response_model=schemas.TerrainResponse,
    summary="Digital Elevation Model and spatial bounds",
    tags=["Terrain"],
)
def get_terrain() -> Dict[str, Any]:
    """Return 64x64 digital elevation model and geographic bounding coordinates."""
    return services.get_terrain()


@app.get(
    "/presets",
    response_model=schemas.PresetsResponse,
    summary="Standard demonstration weather scenarios",
    tags=["Configuration"],
)
def get_presets() -> Dict[str, Any]:
    """Return predefined demonstration scenarios for quick testing in UI."""
    return {"presets": services.get_presets()}


@app.post(
    "/forecast",
    response_model=schemas.ForecastResponse,
    summary="Execute neural surrogate flood rollout",
    tags=["Simulation"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def post_forecast(request: schemas.ForecastRequest) -> Any:
    """Execute rapid neural surrogate flood depth prediction over the 2-hour horizon.

    Status: 501 Not Implemented (Scheduled for Phase 7: Backend Integration).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Forecast endpoint stub: Scheduled for Phase 7 (Backend integration with trained surrogate).",
    )


@app.post(
    "/compare",
    response_model=schemas.CompareResponse,
    summary="Side-by-side surrogate vs numerical solver verification",
    tags=["Simulation"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def post_compare(request: schemas.CompareRequest) -> Any:
    """Run both surrogate and full 2D SWE solver to produce side-by-side comparison and metrics.

    Status: 501 Not Implemented (Scheduled for Phase 7: Backend Integration).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Compare endpoint stub: Scheduled for Phase 7 (Backend integration with hydrodynamic solver).",
    )

