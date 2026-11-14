"""Probe running live FastAPI backend server without starlette TestClient.

Runs uvicorn.Server in a background thread in the same process with HYDRO_MODE=real,
probes /health, /config, /terrain, /presets, /forecast, and /compare with httpx,
measures response codes, latencies, raw and gzip payload sizes, and top-level keys,
then cleanly stops the server.

Phase: Phase 4 & Step 3 Live Verification
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import threading
import time
from typing import Any, Dict

from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import httpx
import uvicorn
from backend.app import app

DEFAULT_PARAMS = {
    "rain_intensity_mmhr": 80.0,
    "rain_duration_min": 45.0,
    "rain_shape": "constant",
    "drain_capacity_mmhr": 0.0,
    "horizon_steps": 120,
    "frame_stride": 1,
}


def run_probe(port: int = 8000) -> bool:
    os.environ["HYDRO_MODE"] = "real"

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    client = httpx.Client()

    try:
        # Wait up to 10 seconds for server startup
        started = False
        t_wait_start = time.perf_counter()
        while time.perf_counter() - t_wait_start < 10.0:
            try:
                r = client.get(f"{base_url}/health", timeout=1.0)
                if r.status_code == 200:
                    started = True
                    break
            except Exception:
                time.sleep(0.2)

        if not started:
            print("[FATAL] Timed out waiting for server /health endpoint.", file=sys.stderr)
            return False

        print(f"[Live Server] Server up and healthy! Probing endpoints...\n", flush=True)
        print("=" * 105, flush=True)
        print(f"{'ENDPOINT':<12} {'STATUS':<8} {'LATENCY (ms)':<14} {'RAW SIZE':<14} {'GZIP SIZE':<14} {'IS_MOCK':<10} {'TOP-LEVEL KEYS'}", flush=True)
        print("=" * 105, flush=True)

        endpoints = [
            ("GET", "/health", None, 5.0),
            ("GET", "/config", None, 5.0),
            ("GET", "/terrain", None, 10.0),
            ("GET", "/presets", None, 5.0),
            ("POST", "/forecast", DEFAULT_PARAMS, 15.0),
            ("POST", "/compare", DEFAULT_PARAMS, 60.0),
        ]

        all_ok = True

        for method, path, body, timeout in endpoints:
            url = f"{base_url}{path}"
            t0 = time.perf_counter()
            try:
                if method == "GET":
                    resp = client.get(url, timeout=timeout)
                else:
                    resp = client.post(url, json=body, timeout=timeout)

                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                raw_bytes = resp.content
                raw_size_str = f"{len(raw_bytes) / 1024:.1f} KB" if len(raw_bytes) > 1024 else f"{len(raw_bytes)} B"
                if len(raw_bytes) > 1024 * 1024:
                    raw_size_str = f"{len(raw_bytes) / (1024*1024):.2f} MB"

                gzip_bytes = gzip.compress(raw_bytes)
                gzip_size_str = f"{len(gzip_bytes) / 1024:.1f} KB" if len(gzip_bytes) > 1024 else f"{len(gzip_bytes)} B"

                # Parse JSON
                try:
                    data = resp.json()
                    top_keys = list(data.keys()) if isinstance(data, dict) else [f"list[{len(data)}]"]
                    is_mock_val = data.get("is_mock", None) if isinstance(data, dict) else None
                    if is_mock_val is None and "surrogate" in data:
                        is_mock_val = data.get("surrogate", {}).get("model_name", "") == "mock-v0"
                except Exception:
                    top_keys = ["(non-JSON)"]
                    is_mock_val = None

                is_mock_str = str(is_mock_val) if is_mock_val is not None else "N/A"
                print(
                    f"{path:<12} {resp.status_code:<8} {elapsed_ms:<14.1f} {raw_size_str:<14} {gzip_size_str:<14} {is_mock_str:<10} {top_keys[:5]}",
                    flush=True,
                )

                if resp.status_code != 200:
                    all_ok = False
                    print(f"  [ERROR] Non-200 response on {path}: {resp.text[:300]}", file=sys.stderr)

            except Exception as e:
                all_ok = False
                print(f"{path:<12} ERROR    {(time.perf_counter() - t0)*1000.0:<14.1f} N/A            N/A            N/A        {str(e)[:40]}", flush=True)

        print("=" * 105, flush=True)
        return all_ok

    finally:
        print("\n[Live Server] Stopping server...", flush=True)
        server.should_exit = True
        time.sleep(0.5)
        print("[Live Server] Server stopped cleanly.", flush=True)


if __name__ == "__main__":
    success = run_probe(port=8000)
    sys.exit(0 if success else 1)
