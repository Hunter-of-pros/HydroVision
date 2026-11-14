"""Generate static fixture JSON files for frontend testing and API contract verification.

Uses hydrovision_ml.mock to generate deterministic reference payloads.
Writes:
- fixtures/forecast_example.json (compact: 5 sampled frames with stride note)
- fixtures/compare_example.json (side-by-side comparison with metrics)
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from hydrovision_ml import mock


def generate_fixtures() -> None:
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
    }

    print("[1/2] Generating fixtures/forecast_example.json from mock...")
    full_forecast = mock.forecast(params)

    # Subsample to 5 representative frames (indices 0, 30, 60, 90, 120) for compact fixture
    stride_indices = [0, 30, 60, 90, 120]
    subsampled_times = [full_forecast["times_s"][i] for i in stride_indices]
    subsampled_frames = [full_forecast["depth_frames"][i] for i in stride_indices]

    compact_forecast = {
        "note": (
            "Fixture contains 5 sampled frames (indices 0, 30, 60, 90, 120) for unit tests "
            "and frontend UI mockup. Full production forecast returns 121 frames x 64 x 64."
        ),
        "contract_version": "1.0",
        "times_s": subsampled_times,
        "depth_frames": subsampled_frames,
        "rain_series_mmhr": full_forecast["rain_series_mmhr"],
        "peak_depth_m": full_forecast["peak_depth_m"],
        "flooded_area_m2": full_forecast["flooded_area_m2"],
        "inference_time_ms": full_forecast["inference_time_ms"],
        "model_name": full_forecast["model_name"],
        "frame_stride": 30,
    }

    forecast_path = fixtures_dir / "forecast_example.json"
    with open(forecast_path, "w", encoding="utf-8") as f:
        json.dump(compact_forecast, f, indent=2)
    print(f" -> Wrote {forecast_path} ({forecast_path.stat().st_size} bytes)")

    print("[2/2] Generating fixtures/compare_example.json from mock...")
    # Fast solver mock run (without slow sleep for fixture generation)
    # Using internal helper directly to avoid 1.5s delay during build
    rain_series = mock._build_rain_series(45.0, 80.0, "constant", 120)
    solv_frames, solv_peak, _ = mock._simulate_water_spread(
        rain_series=rain_series,
        drain_capacity_mmhr=0.0,
        horizon_steps=120,
        noise_seed=42,
    )
    solv_result = {
        "times_s": [full_forecast["times_s"][i] for i in stride_indices],
        "depth_frames": [solv_frames[i] for i in stride_indices],
        "rain_series_mmhr": rain_series,
        "peak_depth_m": round(solv_peak, 3),
        "solve_time_s": 1.52,
        "solver_name": "swe-local-inertial-mock",
        "frame_stride": 30,
    }

    metrics = mock.compute_metrics(
        surrogate_frames=full_forecast["depth_frames"],
        solver_frames=solv_frames,
        params=params,
    )

    compare_fixture = {
        "note": "Fixture contains 5 sampled frames comparing surrogate vs solver with computed metrics.",
        "contract_version": "1.0",
        "surrogate": compact_forecast,
        "solver": solv_result,
        "metrics": metrics,
    }

    compare_path = fixtures_dir / "compare_example.json"
    with open(compare_path, "w", encoding="utf-8") as f:
        json.dump(compare_fixture, f, indent=2)
    print(f" -> Wrote {compare_path} ({compare_path.stat().st_size} bytes)")


if __name__ == "__main__":
    generate_fixtures()

