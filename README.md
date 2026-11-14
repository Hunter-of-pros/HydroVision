# HydroVision — Flood forecasts in seconds, not hours.

HydroVision is an edge-accessible, physics-informed neural surrogate framework that simulates 2 hours of urban street flood dynamics in under 50 milliseconds. By coupling high-resolution digital topography with deep autoregressive learning and hard physical constraints, HydroVision transforms heavy computational fluid dynamics into instantaneous visual intelligence for city planners, first responders, and municipal engineers.

- **USP 1**: Predicts floods in seconds on a live rainfall-driven map.
- **USP 2**: Proves every forecast against the full simulator.

---

## Problem Statement & Requirements

**Problem Statement PS 1.2**: *Physics-Informed Neural Surrogate for Real-Time Urban Flood Forecasting*  
*Organized by Gradient Club, Department of AIML, BMS College of Engineering.*

### Requirements Checklist

| # | Hackathon Requirement | Responsible Component | Status |
|---|---|---|---|
| **REQ-1** | Ingestion of real/synthetic DEM & spatial slope calculation | `hydrovision_ml/terrain/dem.py` | Not started |
| **REQ-2** | 2D Shallow Water Equations hydrodynamic numerical ground truth | `hydrovision_ml/solver/swe_solver.py` | Not started |
| **REQ-3** | Diverse rainfall scenario generation (LHS sampling) & dataset splits | `hydrovision_ml/data/generate_dataset.py` | Not started |
| **REQ-4** | 2D Neural surrogate model predicting spatial depth evolution | `hydrovision_ml/surrogate/model.py` | Not started |
| **REQ-5** | Physics-informed loss (mass conservation & non-negative depth) | `hydrovision_ml/surrogate/losses.py` | Not started |
| **REQ-6** | Interactive map UI with real-time sliders & side-by-side solver verification | `backend/` & `frontend/` | Not started |

---

## Team & Ownership Boundaries

| Role | Member | Responsibilities | Interface Boundary |
|---|---|---|---|
| **ML Pipeline** | Teammate | Terrain preprocessing, 2D SWE solver, synthetic dataset generation, surrogate training, physics losses, and evaluation metrics | Package `hydrovision_ml` (adhering to `docs/CONTRACT.md`) |
| **Backend & Serving** | Vikas M | FastAPI web service, parameter validation, GZip streaming, mock/real mode toggle, and benchmark orchestration | Imports **ONLY** `hydrovision_ml` |
| **Frontend UI** | Vikas M | React + Vite interactive dashboard, Leaflet map canvas overlay, hyetograph sliders, and dual comparison player | Communicates **ONLY** via HTTP REST (`VITE_API_URL`) |

---

## Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+ (for frontend)

### 2. Environment Setup & Installation
```bash
# Clone and enter repository
cd hydrovision

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Generate Static Fixtures
```bash
make fixtures
```

### 4. Start the Mock Backend
Unblock frontend development immediately without waiting for trained ML weights:
```bash
make mock-backend
# Running at http://localhost:8000 (Swagger docs: http://localhost:8000/docs)
```

### 5. Run the Test Suite
```bash
make test
```

### 6. Connect the Frontend
In another terminal:
```bash
cd frontend
cp .env.example .env
# VITE_API_URL=http://localhost:8000
npm install
npm run dev
# Running at http://localhost:5173
```

---

## Project Structure

```
hydrovision/
├── README.md                      # Project overview, requirements checklist, quick start
├── .gitignore                     # Git ignore rules for virtualenvs, caches, heavy artifacts
├── requirements.txt               # Pinned Python dependencies for ML and Backend
├── Makefile                       # Developer shortcuts (setup, test, mock-backend, fixtures, smoke)
├── config.json                    # Contract v1.0 specifications, grid geometry, parameter bounds
├── docs/
│   ├── CONTRACT.md                # Strict data contract v1.0 between ML, Backend, and Frontend
│   ├── ARCHITECTURE.md            # Detailed system design, data flows, and ML pipeline spec
│   ├── DEM_HOWTO.md               # Guide to acquiring, cropping, and conditioning DEMs
│   └── DEMO_SCRIPT.md             # 5-minute hackathon presentation outline and demo flow
├── hydrovision_ml/                # Core Python ML package (Teammate)
│   ├── __init__.py                # Package initialization exporting public API
│   ├── api.py                     # Public API contract stubs raising NotImplementedError
│   ├── mock.py                    # Deterministic, working mock of terrain, rollout, and solver
│   ├── config.py                  # Loads config.json and exports physical constants
│   ├── terrain/                   # DEM ingestion, slope derivation, and synthetic relief
│   │   ├── __init__.py
│   │   └── dem.py
│   ├── solver/                    # Hydrodynamic 2D Shallow Water Equations solver
│   │   ├── __init__.py
│   │   ├── swe_solver.py
│   │   └── scenarios.py
│   ├── data/                      # Batch simulation and dataset split generation
│   │   ├── __init__.py
│   │   └── generate_dataset.py
│   ├── surrogate/                 # Neural surrogate architectures, losses, and training
│   │   ├── __init__.py
│   │   ├── model.py
│   │   ├── losses.py
│   │   ├── train.py
│   │   └── rollout.py
│   └── eval/                      # Formal hydrological metrics, benchmarking, and plots
│       ├── __init__.py
│       ├── metrics.py
│       ├── benchmark.py
│       └── plots.py
├── artifacts/                     # Versioned artifacts (gitignored except .gitkeep)
│   ├── models/.gitkeep            # best.pt, normalizer.json
│   ├── data/.gitkeep              # terrain.npz, train/val/test splits
│   └── reports/.gitkeep           # results.json, diagnostic plots
├── fixtures/                      # Compact reference JSONs for unit tests and frontend dev
│   ├── forecast_example.json      # 5 sampled frames with stride note
│   └── compare_example.json       # Side-by-side comparison with metrics
├── backend/                       # FastAPI application (Vikas)
│   ├── __init__.py
│   ├── app.py                     # FastAPI server with CORS, GZip, /health, /config, /terrain
│   ├── schemas.py                 # Pydantic request/response models conforming to CONTRACT.md
│   ├── services.py                # Service orchestration layer switching mock/real via HYDRO_MODE
│   └── README.md                  # Backend setup, endpoint documentation, and running instructions
├── frontend/                      # React + Vite web dashboard (Vikas)
│   ├── README.md                  # Frontend setup, component overview, and state flow
│   └── .env.example               # Environment variables (VITE_API_URL=http://localhost:8000)
├── tests/                         # Automated test suite
│   ├── test_config.py             # Validates config.json schema and numerical bounds
│   ├── test_mock_contract.py      # Verifies mock obeys all shapes, non-negativity, and keys
│   ├── test_api_shapes.py         # xfail tests for upcoming real ML implementation
│   └── test_backend_health.py     # End-to-end endpoint tests via FastAPI TestClient
└── scripts/                       # Developer automation scripts
    ├── run_backend.sh             # Shell script to start backend server
    ├── smoke_test.py              # Automated smoke test testing all API routes
    └── make_fixtures.py           # Generates static test fixtures from mock
```

---

## Mock vs. Real Mode (`HYDRO_MODE`)

The backend dynamically toggles between mock and real execution using the `HYDRO_MODE` environment variable:

- **`HYDRO_MODE=mock` (Default)**: Uses `hydrovision_ml.mock`. Serves synthetic 64x64 topography, realistic rain runoff accumulation, and a simulated 1.5-second solver without needing PyTorch models or trained weights.
- **`HYDRO_MODE=real`**: Uses `hydrovision_ml.api`. Connects directly to the trained neural surrogate (`artifacts/models/best.pt`) and real numerical SWE solver.

---

## Evaluation Benchmark & Verification

> *Report speed-up with its setup (hardware, grid, batch size).*

| Metric | Target Goal | Real Surrogate (`best.pt`) | Baseline SWE Solver | Notes |
|---|---|---|---|---|
| **Mean Absolute Error (MAE)** | $< 0.05\text{ m}$ | TBD: Phase 6 | Ground Truth | Evaluated across all wet/dry grid cells |
| **Root Mean Square Error (RMSE)**| $< 0.10\text{ m}$ | TBD: Phase 6 | Ground Truth | Penalizes severe local depth errors |
| **Peak Depth Error** | $< 0.08\text{ m}$ | TBD: Phase 6 | Ground Truth | $|\max(\hat{h}) - \max(h)|$ |
| **Inundation IoU (Wet cells $\ge 5\text{ cm}$)**| $> 0.85$ | TBD: Phase 6 | Ground Truth | Critical Success Index for flood extent |
| **Mass Balance Relative Error** | $< 1.0\%$ | TBD: Phase 6 | Ground Truth | Enforced via physics conservation loss |
| **Inference Latency (120 steps)** | $< 50\text{ ms}$ | TBD: Phase 6 | $\approx 1500\text{ ms}$ | Benchmarked on standard CPU, 64x64 grid |
| **Speedup Factor** | $> 30\times$ | TBD: Phase 6 | $1.0\times$ | Solver Runtime / Surrogate Runtime |

---

## Limitations & Assumptions

1. **Single Catchment Focus**: Pre-calibrated for a $2.56\text{ km} \times 2.56\text{ km}$ urban neighborhood ($64 \times 64$ cells at $40\text{ m}$ resolution).
2. **Simplified Numerical Ground Truth**: Benchmark solver employs a 2D local-inertial formulation rather than full Navier-Stokes, omitting subsurface pipe backflow.
3. **Spatially Uniform Rainfall & Drainage**: Rainfall and drainage capacity are treated as spatially uniform rates across the domain.
4. **Surrogate Reproduces Solver**: The neural model learns the physical approximations of the numerical solver, not field-sensor observations directly.
5. **Tentative Targets**: All accuracy and latency numbers are target thresholds until empirically measured in Phase 6.

---

## Contribution Workflow

1. **Branching**: Each contributor works on their assigned feature branch (`feature/ml-<name>` or `feature/backend-<name>`).
2. **Pull Requests**: Pull requests merge into `main` after automated tests pass.
3. **Contract Changes**: Any modification to `config.json` or `docs/CONTRACT.md` (keys, shapes, units, parameter boundaries) requires explicit sign-off from both teammates and a version increment.

---

## Project Roadmap & Status

- [ ] **Phase 1: Terrain Ingestion** — DEM loading, reprojection, slope derivation (`dem.py`).
- [ ] **Phase 2: Numerical Hydrodynamic Solver** — 2D SWE local-inertial solver (`swe_solver.py`, `scenarios.py`).
- [ ] **Phase 3: Dataset Generation** — Latin Hypercube scenario sampling & dataset splits (`generate_dataset.py`).
- [ ] **Phase 4: Baseline Neural Surrogate** — 2D U-Net rollout predicting depth increments (`model.py`, `rollout.py`).
- [ ] **Phase 5: Physics Loss & Stability Training** — Mass conservation loss & multi-step unrolling (`losses.py`, `train.py`).
- [ ] **Phase 6: Formal Evaluation & Benchmarking** — Metric suite, speedup benchmarks, and diagnostic plots (`metrics.py`, `benchmark.py`).
- [x] **Phase 7: Backend Integration** — FastAPI endpoints (`/health`, `/config`, `/terrain`, `/presets`, `/forecast`, `/compare`) with mock/real toggle (`app.py`, `services.py`).
- [x] **Phase 8: Frontend Map Dashboard** — Interactive canvas flood map, hyetograph sliders, timeline scrubber, and side-by-side solver verification scorecard (`frontend/`).
- [ ] **Phase 9: Final Integration & Demo Polish** — Full end-to-end rehearsal using `docs/DEMO_SCRIPT.md`.

---

## Credits & References

TODO: add references

