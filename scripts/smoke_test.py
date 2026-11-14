"""Smoke test script for HydroVision backend API.

Calls every endpoint, verifies status codes, and prints a clear PASS/FAIL report table.
Supports testing against a live HTTP URL (default: http://localhost:8000) or
direct in-process testing via FastAPI TestClient when no server is running.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from typing import Any, Dict, List, Tuple


def _run_via_testclient() -> List[Tuple[str, str, int, int, str]]:
    """Execute smoke test directly in-process using TestClient."""
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)
    results = []

    # 1. GET /health (expects 200)
    resp = client.get("/health")
    ok = resp.status_code == 200 and resp.json().get("status") == "ok"
    results.append(("GET", "/health", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 2. GET /config (expects 200)
    resp = client.get("/config")
    ok = resp.status_code == 200 and "grid" in resp.json()
    results.append(("GET", "/config", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 3. GET /terrain (expects 200)
    resp = client.get("/terrain")
    ok = resp.status_code == 200 and resp.json().get("shape") == [64, 64]
    results.append(("GET", "/terrain", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 4. GET /presets (expects 200)
    resp = client.get("/presets")
    ok = resp.status_code == 200 and "presets" in resp.json()
    results.append(("GET", "/presets", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 5. POST /forecast (expects 200)
    sample_payload = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 120,
        "frame_stride": 10,
    }
    resp = client.post("/forecast", json=sample_payload)
    ok = resp.status_code == 200 and "depth_frames" in resp.json()
    results.append(("POST", "/forecast", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 6. POST /compare (expects 200)
    compare_payload = {
        "rain_intensity_mmhr": 80.0,
        "rain_duration_min": 45.0,
        "rain_shape": "constant",
        "drain_capacity_mmhr": 0.0,
        "horizon_steps": 10,  # Fast run for smoke test
        "frame_stride": 5,
    }
    resp = client.post("/compare", json=compare_payload)
    ok = resp.status_code == 200 and "metrics" in resp.json()
    results.append(("POST", "/compare", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 7. GET /results (expects 200)
    resp = client.get("/results")
    ok = resp.status_code == 200 and "ablation" in resp.json()
    results.append(("GET", "/results", 200, resp.status_code, "PASS" if ok else "FAIL"))

    # 8. GET /weather/live (expects 200)
    resp = client.get("/weather/live")
    ok = resp.status_code == 200 and "temperature_c" in resp.json()
    results.append(("GET", "/weather/live", 200, resp.status_code, "PASS" if ok else "FAIL"))

    return results


def _run_via_http(base_url: str) -> List[Tuple[str, str, int, int, str]]:
    """Execute smoke test against a live running HTTP server."""
    import httpx

    results = []
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        # 1. GET /health
        resp = client.get("/health")
        ok = resp.status_code == 200 and resp.json().get("status") == "ok"
        results.append(("GET", "/health", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 2. GET /config
        resp = client.get("/config")
        ok = resp.status_code == 200 and "grid" in resp.json()
        results.append(("GET", "/config", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 3. GET /terrain
        resp = client.get("/terrain")
        ok = resp.status_code == 200 and resp.json().get("shape") == [64, 64]
        results.append(("GET", "/terrain", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 4. GET /presets
        resp = client.get("/presets")
        ok = resp.status_code == 200 and "presets" in resp.json()
        results.append(("GET", "/presets", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 5. POST /forecast
        sample_payload = {
            "rain_intensity_mmhr": 80.0,
            "rain_duration_min": 45.0,
            "rain_shape": "constant",
            "drain_capacity_mmhr": 0.0,
            "horizon_steps": 120,
            "frame_stride": 10,
        }
        resp = client.post("/forecast", json=sample_payload)
        ok = resp.status_code == 200 and "depth_frames" in resp.json()
        results.append(("POST", "/forecast", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 6. POST /compare
        compare_payload = {
            "rain_intensity_mmhr": 80.0,
            "rain_duration_min": 45.0,
            "rain_shape": "constant",
            "drain_capacity_mmhr": 0.0,
            "horizon_steps": 10,  # Fast run for smoke test
            "frame_stride": 5,
        }
        resp = client.post("/compare", json=compare_payload)
        ok = resp.status_code == 200 and "metrics" in resp.json()
        results.append(("POST", "/compare", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 7. GET /results
        resp = client.get("/results")
        ok = resp.status_code == 200 and "ablation" in resp.json()
        results.append(("GET", "/results", 200, resp.status_code, "PASS" if ok else "FAIL"))

        # 8. GET /weather/live
        resp = client.get("/weather/live")
        ok = resp.status_code == 200 and "temperature_c" in resp.json()
        results.append(("GET", "/weather/live", 200, resp.status_code, "PASS" if ok else "FAIL"))

        return results


def main() -> None:
    base_url = os.getenv("API_URL", "http://localhost:8000")
    print("=" * 65)
    print(" HydroVision Backend API Smoke Test")
    print("=" * 65)

    mode_used = "live HTTP"
    try:
        import httpx
        # Quick ping to see if server is up
        httpx.get(f"{base_url}/health", timeout=1.0)
        results = _run_via_http(base_url)
    except Exception:
        mode_used = "in-process TestClient (server not active on port 8000)"
        results = _run_via_testclient()

    print(f"Target: {base_url} ({mode_used})\n")
    print(f"{'METHOD':<8} {'ENDPOINT':<15} {'EXPECTED':<10} {'ACTUAL':<10} {'RESULT':<8}")
    print("-" * 65)

    all_passed = True
    for method, endpoint, expected, actual, result in results:
        status_flag = "PASS" if result == "PASS" else "FAIL"
        if status_flag == "FAIL":
            all_passed = False
        print(f"{method:<8} {endpoint:<15} {expected:<10} {actual:<10} {status_flag:<8}")

    print("-" * 65)
    if all_passed:
        print(">> ALL ENDPOINTS PASSED SMOKE TEST <<")
        sys.exit(0)
    else:
        print(">> ONE OR MORE ENDPOINTS FAILED SMOKE TEST <<")
        sys.exit(1)


if __name__ == "__main__":
    main()

