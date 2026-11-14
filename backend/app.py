"""FastAPI web server skeleton for HydroVision.

Owner: Backend (Vikas)
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend import schemas, services

app = FastAPI(
    title="HydroVision API",
    description="Physics-informed neural surrogate backend for real-time urban flood forecasting.",
    version="1.0.0",
)

# Exception handler for clear, readable Pydantic 422 validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format Pydantic schema validation failures into clean, descriptive error messages."""
    messages = []
    for err in exc.errors():
        field = " -> ".join(str(part) for part in err.get("loc", []) if part != "body")
        msg = err.get("msg", "Invalid value")
        input_val = err.get("input", None)
        if input_val is not None and not isinstance(input_val, dict):
            messages.append(f"Field '{field}': {msg} (received {input_val})")
        else:
            messages.append(f"Field '{field}': {msg}")
    error_summary = "; ".join(messages)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": error_summary,
            "errors": exc.errors(),
            "message": error_summary,
        },
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
)
def post_forecast(request: schemas.ForecastRequest) -> Dict[str, Any]:
    """Execute rapid neural surrogate flood depth prediction over the 2-hour horizon."""
    if not services.is_mock_mode():
        health = services.get_health()
        if not health.get("model_loaded"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Surrogate model unavailable: HYDRO_MODE=real is enabled but surrogate model weights (artifacts/models/best.pt) failed to load. The system will not silently fallback to mock data.",
            )
    try:
        return services.forecast(request.model_dump())
    except (NotImplementedError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Surrogate model unavailable: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast simulation failed: {e}",
        )


@app.post(
    "/compare",
    response_model=schemas.CompareResponse,
    summary="Side-by-side surrogate vs numerical solver verification",
    tags=["Simulation"],
)
def post_compare(request: schemas.CompareRequest) -> Dict[str, Any]:
    """Run both surrogate and full 2D SWE solver to produce side-by-side comparison and metrics."""
    if not services.is_mock_mode():
        health = services.get_health()
        if not health.get("model_loaded"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Comparison simulation unavailable: HYDRO_MODE=real is enabled but model weights failed to load.",
            )
    try:
        return services.compare(request.model_dump())
    except (NotImplementedError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Comparison simulation unavailable: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison simulation failed: {e}",
        )


@app.get(
    "/results",
    response_model=schemas.EvalSummaryResponse,
    summary="Retrieve empirical evaluation and ablation benchmark summary",
    tags=["Evaluation"],
)
def get_results() -> Dict[str, Any]:
    """Serve empirical evaluation benchmark results.

    Returns results/eval_summary.json if available; otherwise falls back to
    results/eval_summary.mock.json with is_mock=True. Returns 404 if neither exists.
    """
    return services.get_eval_results()


@app.get(
    "/weather/live",
    response_model=schemas.LiveWeatherResponse,
    summary="Retrieve live real-time weather and rainfall rate for Bellandur catchment",
    tags=["Weather"],
)
def get_live_weather() -> Dict[str, Any]:
    """Return real-time weather observations (temperature, precipitation, mm/hr rainfall) for Bellandur catchment."""
    return services.get_live_weather()



