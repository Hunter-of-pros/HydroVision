# HydroVision Comprehensive Status Audit (Read-Only)
_Timestamp: 2026-11-14 21:35 IST_
_Audit Scope: Full Repository, ML Pipeline, Data, Backend, Frontend, and Infrastructure_

---

## 1. ENVIRONMENT
- **Current Directory:** `C:\Users\Khubaib\OneDrive\Desktop\HydroVison`
- **Operating System:** `Windows-11-10.0.26300-SP0`
- **Python Version:** `3.15.2 (tags/v3.15.2:5e58eaa, Oct 25 2026, 17:27:03) [MSC v.1951 64 bit (AMD64)]`
- **OneDrive Path:** `True` (Repo is located inside `C:\Users\Khubaib\OneDrive\Desktop\HydroVison`)
- **Package Import Audit:**
  - `torch`: `2.15.0+cpu`
  - `numpy`: `2.5.4`
  - `scipy`: `1.18.1`
  - `matplotlib`: `3.11.2`
  - `rasterio`: `1.5.2`
  - `numba`: `ImportError (No module named 'numba')`
  - `fastapi`: `0.162.7`
  - `uvicorn`: `0.54.0`
  - `pytest`: `9.2.0`
- **Hardware Acceleration & Compute Resources:**
  - `torch.cuda.is_available()`: `False` (Official PyTorch CUDA wheels for Python 3.15 are not yet released; CPU build installed)
  - `CPU Name`: `12th Gen Intel(R) Core(TM) i9-12900H`
  - `Physical Cores`: `14`
  - `Logical Processors (Threads)`: `20`
  - `System RAM`: `15.69 GB` Total (`1.80 GB` Free / Available at check)

---

## 2. GIT
- **Current Branch:** `feature/ml-pipeline`
- **`git status --short`:**
  *(Working tree clean; no unstaged or uncommitted changes)*
- **`git log --oneline -15`:**
  ```text
  cfeec30 Phase 1A: real Marathahalli-Bellandur terrain (64x64)
  947a242 fix(api): include model_loaded flag in get_model_info for degraded health check
  c725949 Merge remote-tracking branch 'origin/main' into feature/ml-pipeline
  4870673 chore: ignore raster and tar files in .gitignore
  c75d003 Merge pull request #1 from Hunter-of-pros/feature/backend-frontend
  bf37527 docs: update README with one-command run, architecture diagram, demo script, judge QA, and PR description
  5a9b08e feat(resilience): add offline fallback fixtures, real-mode 503 handling, illustrative hazard levels, and synthetic terrain badge
  81541b3 Phase 0: audit, solver validation, speed feasibility probe
  2f084db perf(api-ui): round depth frames, add 422 error handlers, debounce sliders, and show e2e latency
  2d79f0e feat(history): add run history drawer, scenario saving, and delta comparison view
  685b56c feat(evaluation): add evaluation tab, benchmark schema, mock fallback, and scaling charts
  5125347 feat(acceptance): add model validation suite and ML handoff guide
  e144079 feat(contract-v1.1): add mass conservation proposal, additive series, and budget tests
  8dc7015 feat(honesty): add mock-mode banner, scorecard greying, watermark, and health tests
  a59b903 Merge branch 'feature/backend-frontend' into feature/ml-pipeline
  ```
- **`git branch -a`:**
  ```text
    feature/backend-frontend
  * feature/ml-pipeline
    main
    remotes/origin/HEAD -> origin/main
    remotes/origin/feature/backend-frontend
    remotes/origin/feature/ml-pipeline
    remotes/origin/main
  ```
- **`git remote -v`:**
  ```text
  origin  https://github.com/Hunter-of-pros/HydroVision.git (fetch)
  origin  https://github.com/Hunter-of-pros/HydroVision.git (push)
  ```
- **Unpushed Commits (`origin/feature/ml-pipeline..HEAD`):**
  *(Clean / None; local branch is strictly up to date with remote)*
- **Is `origin/feature/backend-frontend` merged into this branch?**
  `YES, ancestor (merged)` (via merge commit `c725949` and `c75d003`).
- **Tracked Files > 50 MB:**
  *(None; all tracked files are well below 50 MB)*

---

## 3. FILE TREE WITH SIZES
```text
./
  .gitignore (1,232 bytes)
  config.json (913 bytes)
  Makefile (1,595 bytes)
  pytest.ini (112 bytes)
  README.md (6,677 bytes)
  requirements.txt (165 bytes)
  artifacts/
    data/
      terrain.npz (71,782 bytes)
      test.npz (11,228 bytes)
      train.npz (216,530 bytes)
      val.npz (106,526 bytes)
    models/
      .gitkeep (56 bytes)
    reports/
      dem.png (458,998 bytes)
      dem_candidates.png (1,539,788 bytes)
      phase0_runner.py (21,125 bytes)
      solver_benchmark.json (1,136 bytes)
      solver_real_terrain.png (155,863 bytes)
      solver_validation.json (908 bytes)
      speed_probe.py (6,668 bytes)
  backend/
    app.py (6,851 bytes)
    schemas.py (4,968 bytes)
    services.py (8,995 bytes)
  docs/
    ARCHITECTURE.md (5,630 bytes)
    CONTRACT.md (4,930 bytes)
    CONTRACT_v1.1_PROPOSAL.md (4,755 bytes)
    DECISIONS.md (3,311 bytes)
    DEMO_SCRIPT.md (4,034 bytes)
    DEM_HOWTO.md (3,780 bytes)
    eval_summary.schema.json (4,010 bytes)
    EVAL_SUMMARY_SCHEMA.md (4,236 bytes)
    JUDGE_QA.md (3,348 bytes)
    ML_HANDOFF.md (3,673 bytes)
    ML_STATUS.md (1,268 bytes)
    PR_DESCRIPTION.md (4,769 bytes)
    TERRAIN_NOTES.md (4,315 bytes)
    screenshots/
      01_live_forecast.png (11,601 bytes)
      02_solver_verification.png (11,084 bytes)
      03_scenario_comparison.png (11,360 bytes)
      04_evaluation_tab.png (11,506 bytes)
  fixtures/
    compare_example.json (6,440,872 bytes)
    forecast_example.json (3,421,673 bytes)
  frontend/
    package.json (661 bytes)
    package-lock.json (97,379 bytes)
    public/
      compare_example.json (6,440,872 bytes)
      compare_fixture.json (6,440,872 bytes)
      forecast_example.json (3,421,673 bytes)
      forecast_fixture.json (3,421,673 bytes)
      presets_fixture.json (997 bytes)
      terrain_fixture.json (27,850 bytes)
  hydrovision_ml/
    api.py (7,750 bytes)
    config.py (1,498 bytes)
    mock.py (18,294 bytes)
    data/
      generate_dataset.py (9,410 bytes)
      rasters_COP30.tar.gz (78,574 bytes)
    eval/
      benchmark.py (4,942 bytes)
      metrics.py (7,688 bytes)
      plots.py (4,188 bytes)
    solver/
      scenarios.py (5,640 bytes)
      swe_solver.py (8,124 bytes)
    surrogate/
      losses.py (3,875 bytes)
      model.py (3,490 bytes)
      rollout.py (1,920 bytes)
      train.py (3,055 bytes)
    terrain/
      dem.py (12,852 bytes)
  results/
    eval_summary.mock.json (1,305 bytes)
    validation_report.json (3,345 bytes)
  scripts/
    dev.sh (2,374 bytes)
    inspect_dem_candidates.py (8,450 bytes)
    make_fixtures.py (4,140 bytes)
    process_real_terrain.py (11,620 bytes)
    smoke_test.py (3,520 bytes)
    validate_model.py (18,240 bytes)
  tests/
    test_api_shapes.py (2,912 bytes)
    test_backend_health.py (6,850 bytes)
    test_config.py (2,410 bytes)
    test_ml_pipeline.py (6,240 bytes)
    test_mock_contract.py (4,820 bytes)
    test_validation.py (4,980 bytes)
```
- **External Dataset Directories:**
  - `HYDRO_DATA_DIR`: `None`
  - `C:\hydrovision_data`: `EXISTS (164,636 bytes total)`
  - `C:\hydrovision_data\dem`: `EXISTS (164,636 bytes total)`
    - `marathahalli.tif`: `82,318 bytes`
    - `output_hh.tif`: `82,318 bytes`
- **Raw DEM File & Git Check:**
  - `C:/hydrovision_data/dem/marathahalli.tif` exists: `True` (`82,318 bytes`)
  - `*.tif` in `.gitignore`: `True` (patterns `*.tif`, `*.tiff`, `artifacts/data/*.tif`, `artifacts/data/*.tiff` present).

---

## 4. TERRAIN
- **Archive Details (`artifacts/data/terrain.npz`):**
  - Modification Time: `Sat Nov 14 18:37:19 2026`
  - Stored Keys: `['dem_m', 'elevation', 'slope_x', 'slope_y', 'bounds', 'cell_size_m', 'dx_m', 'is_synthetic', 'source', 'smoothing_sigma', 'window_used']`
  - `dem_m`: shape `(64, 64)`, dtype `float32`, min `863.9810 m`, max `901.8050 m`, mean `878.3957 m`
  - `bounds`: `[12.923194, 77.67625, 12.95875, 77.711806]`
  - `cell_size_m` / `dx_m`: `60.9` meters
  - `is_synthetic`: `False`
  - `smoothing_sigma`: `0.8`
  - `window_used`: `[27, 155, 12, 140]`
  - `source`: `Copernicus GLO-30 via OpenTopography, produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved`
- **Plain Classification:** This is the **REAL Marathahalli–Bellandur DEM** (Copernicus GLO-30 cropped to 128×128 native cells and 2× block-mean downsampled to 64×64). It is NOT synthetic.
- **Consistency Check:**
  - `config.json` `grid.cell_size_m`: `60.9`
  - `docs/CONTRACT.md` `Cell Size ($dx, dy$)`: `60.9`
  - Do they match `terrain.npz`: `True`
- **Diagnostic Files Existence & Sizes:**
  - `artifacts/reports/dem.png`: `EXISTS (458,998 bytes)`
  - `artifacts/reports/dem_candidates.png`: `EXISTS (1,539,788 bytes)`
  - `artifacts/reports/solver_real_terrain.png`: `EXISTS (155,863 bytes)`
  - `docs/TERRAIN_NOTES.md`: `EXISTS (4,315 bytes)`

---

## 5. SOLVER
- **Key Solver Parameters (`hydrovision_ml/solver/swe_solver.py`):**
  - **Scheme:** de Almeida & Bates (2012) local-inertial 2D Shallow Water Equations on a regular Cartesian grid.
  - **Manning Roughness ($n$):** `0.035`
  - **CFL Limit / Safety Factor:** `substep_cfl = 0.7`, adaptive $\Delta t_{sub} = \min(60.0 - \text{elapsed}, \max(1.0, \min(5.0, \text{CFL} \cdot \Delta x / \max(c, 0.1))))$.
  - **Drainage Handling:** Infiltration sink term $\Delta h_{drain} = \min(h_{inter}, \Delta t_{sub} \cdot D_{mps})$ bounded strictly by available water volume to enforce mass conservation.
  - **Boundary Handling:** Closed/reflective boundaries by default (`flux_x[:, 0] = -qx[:, 0]`, `flux_x[:, -1] = qx[:, -1]`, `flux_y[0, :] = -qy[0, :]`, `flux_y[-1, :] = qy[-1, :]`).
  - **Inundation Threshold:** `WET_THRESHOLD_M = 0.05 m`.
- **Live Cloudburst Scenario Verification (120 Steps / 2 Hours, 100 mm/hr, Drain=10 mm/hr):**
  - Runtime: `0.283 s` (`solve_time_s: 0.283s`)
  - Smallest Internal Sub-timestep: `5.00 s`
  - Maximum Courant Number: `0.462` (unconditionally stable $< 1.0$)
  - Minimum Water Depth: `0.000000 m` (Strictly non-negative)
  - Maximum Water Depth: `3.2336 m`
  - NaN Count: `0`
  - Cumulative Rain Input: `1,519,128.58 m³`
  - Final Stored Water Volume: `1,270,241.05 m³` (Remaining after cumulative drainage sink)
- **Validation Report Files:**
  - `artifacts/reports/solver_validation.json`: `EXISTS (908 bytes)` (All 6 physics tests: A_bucket, B_drain, C_outlet, D_lake_at_rest, E_monotonicity, F_nonnegativity PASS).
  - `artifacts/reports/solver_benchmark.json`: `EXISTS (1,136 bytes)` (Median `254.58 ms`, P95 `283.21 ms` over 30 scenarios; Speed probe attached).

---

## 6. DATASET
- **Dataset File Audit (`artifacts/data/`):**
  - `artifacts/data/test.npz`: `11,228 bytes`, modified `Sat Nov 14 15:49:08 2026`
    - `depth_frames`: shape `(0, 21, 64, 64)`, dtype `float32` (EMPTY)
    - `rain_series`: shape `(0, 120)`, dtype `float32`
    - `dem`: shape `(64, 64)`, dtype `float32`, min `81.16 m`, max `100.04 m`
    - `num_samples`: `0`
  - `artifacts/data/train.npz`: `216,530 bytes`, modified `Sat Nov 14 15:49:08 2026`
    - `depth_frames`: shape `(2, 21, 64, 64)`, dtype `float32`, min `0.0000 m`, max `1.9270 m`, NaNs `0`, wet fraction `10.76%`
    - `rain_series`: shape `(2, 120)`, dtype `float32`
    - `dem`: shape `(64, 64)`, dtype `float32`, min `81.16 m`, max `100.04 m`
    - `num_samples`: `2`
  - `artifacts/data/val.npz`: `106,526 bytes`, modified `Sat Nov 14 15:49:08 2026`
    - `depth_frames`: shape `(1, 21, 64, 64)`, dtype `float32`, min `0.0000 m`, max `0.7769 m`, NaNs `0`, wet fraction `3.01%`
    - `rain_series`: shape `(1, 120)`, dtype `float32`
    - `dem`: shape `(64, 64)`, dtype `float32`, min `81.16 m`, max `100.04 m`
    - `num_samples`: `1`
  - `extrapolation.npz`: `MISSING`
  - Separate metadata JSON files in `artifacts/data/`: `MISSING` (`[]`)
- **Terrain Hash & Staleness Verdict:**
  - Current `terrain.npz` SHA256: `d63ba5b03e5806482cdcf6b2abf6ee6d027576c5892efad13ca810e6b6500567` (Elevation range 863.98m – 901.81m)
  - Embedded DEM in existing dataset splits: Elevation range 81.16m – 100.04m (Old synthetic terrain)
  - **Verdict:** The existing dataset is **STALE and INCOMPLETE** (only 3 prototype scenarios generated during initial pipeline testing before Phase 1A real DEM was ingested).

---

## 7. MODEL AND TRAINING
- **Surrogate Codebase (`hydrovision_ml/surrogate/`):**
  - `__init__.py` (28 lines): Exports definitions.
  - `losses.py` (106 lines):
    - `def mass_conservation_loss`: `STUB (raises NotImplementedError)`
    - `def nonneg_penalty`: `STUB (raises NotImplementedError)`
    - `def rollout_loss`: `STUB (raises NotImplementedError)`
  - `model.py` (98 lines):
    - `class Normalizer`: Methods `fit`, `transform`, `inverse_transform`, `save`, `load` are all `STUBS (NotImplementedError)`
    - `class UNetSurrogate`: `__init__` and `forward` are `STUBS (NotImplementedError)`
    - `class ConservativeSurrogate`: `__init__` and `forward` are `STUBS (NotImplementedError)`
  - `rollout.py` (53 lines):
    - `def rollout`: `STUB (raises NotImplementedError)`
  - `train.py` (92 lines):
    - `def train`: `STUB (raises NotImplementedError)`
    - `def main`: Argument parser implemented; calls `train()` stub.
- **Model Checkpoints & Training Reports:**
  - `artifacts/models/`: `EMPTY` (contains only `.gitkeep`)
  - `artifacts/models/best.pt`: `MISSING`
  - `train_log*.json`: `MISSING`
  - `baseline_metrics.json`: `MISSING`
  - `ablation.json`: `MISSING`
  - `results.json`: `MISSING`
  - `model_selection.md`: `MISSING`
- **Has any training run ever completed?**
  **NO.** Evidence: `glob("**/*.pt")` across entire repository returns `[]`.

---

## 8. EVALUATION
- **`hydrovision_ml/eval/metrics.py` Execution Test:**
  - Verified working via `compute_all_metrics()` on random inputs:
    ```text
    mae: 0.333
    rmse: 0.408
    peak_depth_error: 0.0
    wet_iou: 1.0
    mass_error: 0.0104
    arrival_time_error_s: 5.7
    speedup: 42.9
    ```
- **Trained Model Evaluation:**
  **NO MODEL** (`artifacts/models/best.pt` does not exist; model rollout evaluation cannot be performed).

---

## 9. ML API (`hydrovision_ml/api.py`)
- **Function Implementation Status:**
  - `api.load_all`: `IMPLEMENTED` (loads static `terrain.npz`; model weight loading is stubbed until weights exist)
  - `api.get_config`: `IMPLEMENTED` (real configuration from `config.json`, 6 top-level keys)
  - `api.get_terrain`: `IMPLEMENTED` (real 64×64 elevation from `terrain.npz`, $dx=60.9\text{ m}$)
  - `api.get_model_info`: `IMPLEMENTED` (`is_mock=False`, `model_name="hydrovision-swe-v1"`, `model_loaded=True`)
  - `api.run_solver`: `IMPLEMENTED` (executes full 2D local-inertial SWE solver; produces 121 frames of shape 64×64 in 0.275s)
  - `api.compute_metrics`: `IMPLEMENTED` (computes MAE, RMSE, peak depth error, Wet IoU, mass balance error, arrival time)
  - `api.forecast`: `STUB` (raises `NotImplementedError: forecast() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing.`)
  - `api.forecast_batch`: `STUB` (raises `NotImplementedError`)
- **Execution Test with Default Scenario (`80 mm/hr, 45 min, 120 steps`):**
  - `get_config()` keys: `['contract_version', 'grid', 'time', 'wet_threshold_m', 'hazard_thresholds', 'params']`
  - `get_terrain()` keys: `['elevation', 'dx_m', 'bounds', 'shape', 'min_elevation', 'max_elevation']`
    - Dimensions: `64x64`, $dx_m$: `60.9`, Bounds: `[12.923194, 77.67625, 12.95875, 77.711806]`
  - `run_solver()` keys: `['times_s', 'depth_frames', 'rain_series_mmhr', 'peak_depth_m', 'flooded_area_m2', 'solve_time_s', 'solver_name']`
    - `depth_frames`: shape `(121, 64, 64)`, dtype `float64`
    - `times_s`: length `121`
    - `rain_series_mmhr`: length `120`
    - `solve_time_s`: `0.275 s`
- **Contract Checks on `forecast()`:** `NOT IMPLEMENTED` (Phase 4 surrogate pending).

---

## 10. BACKEND AND FRONTEND
- **Backend In-Process API Test (`backend/app.py`):**
  - **`HYDRO_MODE=mock`:**
    - `GET  /health`    $\to$ `200` (`63.9 ms`) | keys: `['status', 'model_loaded', 'is_mock', 'contract_version']`
    - `GET  /config`    $\to$ `200` (`4.5 ms`)  | keys: `['contract_version', 'grid', 'time', 'wet_threshold_m', 'hazard_thresholds', 'params']`
    - `GET  /terrain`   $\to$ `200` (`5.1 ms`)  | keys: `['elevation', 'dx_m', 'bounds', 'shape', 'min_elevation', 'max_elevation', 'is_synthetic']`
    - `GET  /presets`   $\to$ `200` (`3.7 ms`)  | keys: `['presets']`
    - `POST /forecast`  $\to$ `200` (`130.2 ms`)| keys: `['times_s', 'depth_frames', 'rain_series_mmhr', 'peak_depth_m', 'flooded_area_m2', 'inference_time_ms', 'model_name', 'frame_stride', 'volume_m3_series', 'cum_rain_m3_series', 'cum_drain_m3_series', 'cum_outflow_m3_series', 'mass_residual_series']`
    - `POST /compare`   $\to$ `200` (`1876.7 ms`)| keys: `['surrogate', 'solver', 'metrics', 'model_name']`
  - **`HYDRO_MODE=real`:**
    - `GET  /health`    $\to$ `200` (`3.7 ms`)  | keys: `['status', 'model_loaded', 'is_mock', 'contract_version']` (`status: "ok"`)
    - `GET  /config`    $\to$ `200` (`3.4 ms`)  | keys: `['contract_version', 'grid', 'time', 'wet_threshold_m', 'hazard_thresholds', 'params']`
    - `GET  /terrain`   $\to$ `200` (`7.6 ms`)  | keys: `['elevation', 'dx_m', 'bounds', 'shape', 'min_elevation', 'max_elevation', 'is_synthetic']` (serves real DEM)
    - `GET  /presets`   $\to$ `200` (`2.8 ms`)  | keys: `['presets']`
    - `POST /forecast`  $\to$ `503` (`2.6 ms`)  | error detail: `"Surrogate model unavailable. Checkpoint 'artifacts/models/best.pt' not found."`
    - `POST /compare`   $\to$ `503` (`2.4 ms`)  | error detail: `"Surrogate model unavailable. Checkpoint 'artifacts/models/best.pt' not found."`
- **Frontend Codebase & Build:**
  - `package.json` exists: `True`
  - `node_modules` exists: `True`
  - **`npm run build` Result:** `SUCCESS` (Completed in `13.82 s`, output bundles in `dist/`):
    - `dist/index.html`: `0.84 kB`
    - `dist/assets/index-CmGgIfDn.css`: `29.65 kB`
    - `dist/assets/index-DUW0sMzv.js`: `255.25 kB`
  - **Map & Chart Libraries in `package.json`:**
    - `dependencies`: `clsx`, `lucide-react`, `react`, `react-dom`, `tailwind-merge`
    - No external map library (e.g. Leaflet / Mapbox) is installed; MapViewer uses custom HTML5 Canvas rendering.
    - No external charting library (e.g. Chart.js / Recharts) is installed; charts use custom SVG and canvas rendering.
- **Hard-coded 40 m / Old Bounds Grep in `backend/` and `frontend/`:**
  - `backend/schemas.py:25`: `cell_size_m: float = Field(40.0, description="Spatial resolution of each cell in meters.")`
  - `backend/schemas.py:61`: `dx_m: float = Field(40.0, description="Cell size in meters.")`
  - `frontend/public/terrain_fixture.json:1`: Hardcodes old synthetic DEM array and bounds.
  - `frontend/src/components/HazardMetrics.tsx:13`: Comment says `// 40m * 40m = 1600 m2`.
  - `frontend/src/components/MapViewer.tsx:249`: Fallback `{terrain?.dx_m ?? 40}m/cell`.

---

## 11. TESTS
- **`pytest -q` Output:**
  ```text
  XxXXX....................................                                [100%]
  36 passed, 1 xfailed, 4 xpassed, 8 warnings in 6.19s
  ```
- **Test Categorization:**
  - **Failed:** `0`
  - **XFAIL (Expected Failures):**
    - `tests/test_api_shapes.py::test_real_api_forecast` (Real neural surrogate not yet trained)
  - **XPASS (Unexpected Passes due to stale xfail marks):**
    - `tests/test_api_shapes.py::test_real_api_get_terrain`
    - `tests/test_api_shapes.py::test_real_api_run_solver`
    - `tests/test_api_shapes.py::test_real_api_compute_metrics`
    - `tests/test_api_shapes.py::test_real_api_get_model_info`

---

## 12. CONTRACT AND CONFIG CONSISTENCY
- **Comparison Table:**

| Parameter | `config.json` | `hydrovision_ml.config` | `docs/CONTRACT.md` | Consistency |
|---|---|---|---|---|
| Grid Rows | `64` | `64` | `64 rows` | Matched |
| Grid Cols | `64` | `64` | `64 columns` | Matched |
| Cell Size ($dx, dy$) | `60.9 m` | `60.9 m` | `60.9 meters` | Matched |
| Time Step ($\Delta t$) | `60 s` | `60 s` | `60.0 seconds` | Matched |
| Horizon Steps | `120` | `120` | `120 steps` | Matched |
| Wet Threshold | `0.05 m` | `0.05 m` | `0.05 meters` | Matched |
| Rain Intensity Range | `[20, 150]` (default 80) | From config | `[20, 150]` | Matched |
| Rain Duration Range | `[15, 90]` (default 45) | From config | `[15, 90]` | Matched |
| Drain Capacity Range | `[0, 30]` (default 0) | From config | `[0, 30]` | Matched |

- **Mismatches & Inconsistencies:**
  1. `backend/schemas.py:25, 61`: Defaults `cell_size_m` and `dx_m` to `Field(40.0)` instead of `60.9`.
  2. `hydrovision_ml/mock.py:111`: Hardcodes synthetic bounds `[12.920, 77.560, 12.943, 77.583]` while real terrain has `[12.923194, 77.676250, 12.958750, 77.711806]`.
  3. `frontend/public/terrain_fixture.json`: Contains synthetic 40m elevation and bounds.

---

## 13. DOCS AND DELIVERABLES
- `README.md`: `EXISTS (174 lines, non-trivial)`
- `docs/ARCHITECTURE.md`: `EXISTS (162 lines, non-trivial)`
- `docs/CONTRACT.md`: `EXISTS (134 lines, non-trivial)`
- `docs/DECISIONS.md`: `EXISTS (80 lines, non-trivial)`
- `docs/ML_STATUS.md`: `EXISTS (26 lines, non-trivial)`
- `docs/TERRAIN_NOTES.md`: `EXISTS (66 lines, non-trivial)`
- `docs/COLAB.md`: `MISSING`
- `docs/DEMO_SCRIPT.md`: `EXISTS (80 lines, non-trivial)`
- `artifacts/reports/RESULTS.md`: `MISSING`
- `results.json`: `MISSING`
- `slide_assets/`: `MISSING`

---

## 14. SPEED SNAPSHOT
- **Hardware:** Intel Core i9-12900H (14 cores / 20 threads), 16 GB RAM
- **Precision:** NumPy `float64` (hydrodynamic flux computation), `float32` (frame buffers)
- **2D SWE Solver Runtime (1 scenario, 120 steps):**
  - Runtimes over 10 consecutive runs: `[267.8, 276.9, 274.5, 279.4, 278.6, 278.9, 275.3, 273.9, 281.5, 281.1] ms`
  - **Median:** **`277.78 ms`** (`0.278 s`)
- **Surrogate Rollout (1 scenario):** `NO MODEL` (`artifacts/models/best.pt` does not exist)
- **Surrogate Rollout (Batch of 50):** `NO MODEL`

---

## 15. PROBLEMS FOUND

1. **[CRITICAL] Neural surrogate components are stubs:** All classes and functions in `hydrovision_ml/surrogate/` (`model.py`, `losses.py`, `rollout.py`, `train.py`) raise `NotImplementedError`. Evidence: `hydrovision_ml/surrogate/losses.py:35, 65, 95`.
2. **[CRITICAL] Model weights missing:** `artifacts/models/best.pt` does not exist. Evidence: `os.path.exists("artifacts/models/best.pt") == False`.
3. **[CRITICAL] Backend returns 503 in real mode:** When `HYDRO_MODE=real`, endpoints `POST /forecast` and `POST /compare` return `503 Service Unavailable` with message `"Surrogate model unavailable"`. Evidence: `backend/services.py:165`.
4. **[CRITICAL] Dataset is stale and unpopulated:** `artifacts/data/train.npz` has only 2 samples, `val.npz` has 1 sample, `test.npz` has 0 samples, and the embedded DEM contains old synthetic topography (min 81.16m, max 100.04m) rather than the real Marathahalli DEM. Evidence: `train.npz:dem min=81.16 vs terrain.npz min=863.98`.
5. **[IMPORTANT] CPU-only PyTorch environment:** `torch.cuda.is_available() == False` because official PyTorch CUDA wheels for Python 3.15 are not yet available on PyPI/download.pytorch.org. Training must be run on CPU or offloaded to a GPU Colab instance. Evidence: `import torch; torch.cuda.is_available() -> False`.
6. **[IMPORTANT] Backend schemas default to old 40m cell size:** `backend/schemas.py:25, 61` hardcode `Field(40.0)` instead of importing `CELL_SIZE_M` (`60.9`). Evidence: `backend/schemas.py:25`.
7. **[IMPORTANT] Mock mode bounds mismatch:** `hydrovision_ml/mock.py:111` hardcodes synthetic bounds `[12.920, 77.560, 12.943, 77.583]` while real terrain has `[12.923194, 77.676250, 12.958750, 77.711806]`. Evidence: `hydrovision_ml/mock.py:111`.
8. **[IMPORTANT] Missing project deliverables:** `docs/COLAB.md`, `artifacts/reports/RESULTS.md`, `results.json`, and `slide_assets/` are missing from the repository. Evidence: File existence checks in Section 13.
9. **[MINOR] Repository is inside a OneDrive folder:** `C:\Users\Khubaib\OneDrive\Desktop\HydroVison` is tracked by OneDrive file sync, which can introduce background file lock latency during dataset generation or training epochs.
10. **[MINOR] Stale test xfail markers:** `tests/test_api_shapes.py` has `@pytest.mark.xfail` on 4 tests that now pass, producing 4 XPASS notices in pytest. Evidence: `pytest -q -> 36 passed, 1 xfailed, 4 xpassed`.
11. **[MINOR] Static frontend terrain fixture is synthetic:** `frontend/public/terrain_fixture.json` contains 40m synthetic elevation and old bounds rather than the calibrated Marathahalli grid. Evidence: `frontend/public/terrain_fixture.json:1`.

---

## 16. HONEST PROGRESS TABLE

| Item | Status | Evidence Note |
|---|---|---|
| **Terrain real** | **DONE** | Copernicus GLO-30 64×64 grid ($dx=60.9\text{m}$, relief 37.8m) in `artifacts/data/terrain.npz`. |
| **Terrain config updated** | **DONE** | `config.json` `cell_size_m=60.9` and `docs/CONTRACT.md` updated and consistent. |
| **Solver validated** | **DONE** | All 6 physics checks pass in `solver_validation.json`; cloudburst runtime `0.283s`, 0 NaNs. |
| **Dataset generated** | **PARTIAL** | Pipeline in `generate_dataset.py` exists, but only 3 prototype samples exist in `artifacts/data/`. |
| **Dataset matches current terrain** | **NOT STARTED** | Existing `train.npz` DEM has min `81.16m` (stale synthetic), not real Marathahalli DEM (`863.98m`). |
| **Model implemented** | **STUB** | `UNetSurrogate` & `Normalizer` in `surrogate/model.py` raise `NotImplementedError`. |
| **Model trained** | **NOT STARTED** | `artifacts/models/best.pt` does not exist; no training runs have executed. |
| **Physics loss implemented and unit-tested** | **STUB** | `mass_conservation_loss` & `rollout_loss` in `surrogate/losses.py` raise `NotImplementedError`. |
| **Stability training** | **NOT STARTED** | Autoregressive multi-step rollout and scheduled sampling not implemented. |
| **Ablation done** | **NOT STARTED** | `ablation.json` does not exist. |
| **Evaluation numbers** | **PARTIAL** | `eval/metrics.py` fully implemented and tested; waiting for trained checkpoint. |
| **Real API wired** | **PARTIAL** | `api.py` wires terrain, solver, and metrics; `forecast()` raises `NotImplementedError`. |
| **Backend real mode works** | **PARTIAL** | `/health`, `/config`, `/terrain`, `/presets` work in real mode; `/forecast` returns 503. |
| **Frontend builds** | **DONE** | `npm run build` succeeds cleanly in `13.82s` (0 errors). |
| **Frontend shows real forecast** | **NOT STARTED** | Operates against mock mode (`is_mock: true`) because real model weights do not exist. |
| **README results** | **PARTIAL** | `README.md` exists with mock benchmarks; lacks real trained surrogate evaluation. |
| **Slide assets** | **NOT STARTED** | `slide_assets/` folder does not exist. |

---

## 17. TIME ESTIMATE

| Incomplete Item | Estimated Time (Local CPU) | Estimated Time (Colab GPU) | Notes |
|---|---|---|---|
| **1. Dataset Generation** (100–200 scenarios) | 1.0 – 1.5 hours | 0.25 hours | 120-step SWE solver takes ~0.28s/scenario; parallelizable across 14 CPU cores. |
| **2. Surrogate Architecture & Normalizer** | 1.5 – 2.0 hours | 1.5 – 2.0 hours | Implement UNet (~300k params, 7 in channels), Normalizer, and temporal bundling. |
| **3. Physics Losses & Training Loop** | 1.5 – 2.0 hours | 1.5 – 2.0 hours | Mass conservation penalty, non-negativity loss, multi-step autoregressive rollout. |
| **4. Model Training** (50–100 epochs) | 3.0 – 5.0 hours | 0.5 – 0.8 hours | CPU-only PyTorch takes ~3–5 hours; Colab T4/A100 GPU completes in ~30–45 mins. |
| **5. Ablation & Evaluation Metrics** | 1.0 – 1.5 hours | 0.5 hours | Baseline vs Bundled vs Physics Loss benchmark comparisons. |
| **6. API Wiring & Real Backend Verification** | 0.5 – 1.0 hours | 0.5 – 1.0 hours | Wire `api.forecast()`, verify `/forecast` and `/compare` return 200 in real mode. |
| **7. Documentation & Slide Deliverables** | 1.0 – 1.5 hours | 1.0 – 1.5 hours | Write `COLAB.md`, `RESULTS.md`, `results.json`, and export slide figures. |
| **TOTAL REMAINING EFFORT** | **9.5 – 14.5 hours** | **5.5 – 8.0 hours** | **Offloading training to Colab GPU saves ~3–4 hours.** |
