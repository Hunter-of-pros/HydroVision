# HydroVision: Known Issues & Diagnostics

_Last Updated: 2026-11-14_
_Author: ML Pipeline_

This document records persistent non-blocking issues, architectural anomalies, and environment findings identified during Phase 1.5.

---

## 1. FastAPI TestClient Hang on Backend Tests

### Symptom
`tests/test_backend_health.py` and `tests/test_validation.py` hang indefinitely upon invoking `TestClient(app)` when executed on this machine, despite having passed in ~6 seconds during an earlier status audit.

### Stack / Locus
The hang occurs synchronously upon the very first HTTP request (e.g. `client.get("/health")` or `client.post("/forecast")`) inside the Starlette/httpx event loop initialization layer. Standalone non-HTTP unit tests (`test_config.py`, `test_mock_contract.py`, `test_api_shapes.py`, `test_ml_pipeline.py`) continue to pass within seconds.

### Diagnosis
- The exact root cause is currently unproven. The hypothesis that "Python 3.15 is incompatible with TestClient" remains an unverified hypothesis because the tests did pass earlier under Python 3.15.
- Possible environmental causes include background process contention on local network interfaces, socket multiplexing locks in headless PowerShell, or event loop lifespan deadlocks when `uvicorn` was previously bound to `127.0.0.1:8000`.

### Action for Vikas (Backend Owner)
- Check test execution locally on Vikas's machine: `pytest tests/test_backend_health.py tests/test_validation.py -v`.
- If it passes on the backend workstation, this is an environment-specific runner artifact on the development Windows host.
- Do not let this test runner hang block the core ML surrogate training pipeline.

---

## 2. Speed Probe Benchmark Bottleneck & Redesign

### Symptom
The initial speed probe (`scripts/speed_probe.py`) scheduled 10 iterations of a 120-step autoregressive rollout with a batch size of 50 across three thread counts ({4, 8, 12}) on CPU. This required 6,000 full forward passes of batch 50, causing a multi-tens-of-minutes CPU saturation and runner timeout.

### Fix Applied
- Redesigned the probe leanly in `scripts/speed_probe.py`.
- Tested the bundled architecture ($k=5$ temporal bundling) with 7 forward timings and 5 training step timings.
- Used analytical rollout calculations confirmed by a single real 120-step bundled rollout at batch 1 and batch 8.
- The new benchmark completed in ~15 seconds and demonstrated a **2.04× speedup** over the solver at Batch 1 (**131.1 ms** vs 267.0 ms) and **3.75× to 4.17× speedup** batched (64.0 ms/scenario).

---

## 3. Host System Memory & Working Set Constraints

### Finding
- **Total Physical RAM**: 15.692 GB
- **Available RAM**: **1.819 GB** (Target of $\ge 4.0\text{ GB}$ is **NOT MET**).
- **Commit Limit**: 40.633 GB (Commit charge: 32.554 GB, 88% memory load).

### Working Set Analysis
The gap between total RAM (15.7 GB) and available RAM (1.8 GB) is accounted for by host processes:
1. **Web Browsers**: Brave (14 processes, ~1,000 MB) and Google Chrome (24 processes, ~800 MB) consume ~1.8 GB.
2. **IDE & Developer Tools**: VS Code (`Code`, 18 processes, ~1,100 MB), Antigravity IDE (`Antigravity IDE` / `agy` / `msedgewebview2`, ~1,150 MB).
3. **Security / System**: Windows Defender (`MsMpEng`, ~401 MB), Memory Compression (~193 MB).
4. No virtual machines (`vmmem`, `vmmemWSL`, `docker`) or OneDrive sync engines are currently active.

### Impact on Training
The training pipeline must rely on zero-copy memory-mapped file loading (`np.load(path, mmap_mode='r')`) rather than loading the full dataset into RAM. A training batch size of 32 consumes only ~12 MB of dynamic tensor memory, which comfortably fits within the 1.8 GB available headroom.
