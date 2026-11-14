# HydroVision Interface Contract v1.0

> Paste contract v1.0 here

---

## 1. Scope & Ownership Boundaries

This contract establishes the strict interface boundary between:
1. **ML Pipeline** (`hydrovision_ml` package, owned by ML Teammate)
2. **Backend API** (FastAPI service in `backend/`, owned by Vikas)
3. **Frontend UI** (React + Vite in `frontend/`, owned by Vikas)

### Boundary Rules
- The **Backend** imports **ONLY** the top-level `hydrovision_ml` package (or `hydrovision_ml.mock` in mock mode). It does not access raw weights, internal training code, or solver functions directly.
- The **Frontend** talks **ONLY** to the HTTP REST API exposed by the Backend.
- Any change to keys, units, grid shapes, or parameter ranges requires a version bump in `config.json` and mutual agreement from both developers.

---

## 2. Core Conventions & Physical Units

| Dimension / Variable | Canonical Convention | Units | Notes |
|---|---|---|---|
| **Grid Dimensions** | 64 rows x 64 columns | Grid cells | Regular Cartesian mesh |
| **Grid Orientation** | Row 0 = North, Col 0 = West | Spatial index | Row index increases Southward; Col index increases Eastward |
| **Cell Size ($dx, dy$)** | 40.0 meters | $m$ | $64 \times 40 = 2560\text{ m} \approx 2.56\text{ km}$ square catchment |
| **Elevation ($z$)** | Floating point | $m$ (a.s.l.) | Topographic elevation above sea level |
| **Water Depth ($h$)** | Floating point $\ge 0.0$ | $m$ | Above ground surface; no NaNs, no negative values |
| **Rainfall Rate ($R$)** | Floating point | $mm/hr$ | Uniform spatial precipitation over catchment |
| **Drain Capacity ($D$)**| Floating point | $mm/hr$ | Uniform infiltration/drainage rate |
| **Time Step ($\Delta t$)** | 60.0 seconds | $s$ | 1-minute temporal resolution |
| **Horizon ($T$)** | 120 steps | intervals | Total elapsed time: $120 \times 60 = 7200\text{ s} = 2\text{ hours}$ |
| **Output Frames** | 121 frames | frames | $t=0$ (initial dry state) through $t=120$ |
| **Inundation Threshold**| 0.05 meters | $m$ | Cells with $h \ge 0.05\text{ m}$ (5 cm) classified as flooded |

---

## 3. Public API Specification (`hydrovision_ml.api`)

All public functions must adhere to the signatures below. In mock mode, `hydrovision_ml.mock` provides an identical working interface.

### `load_all(model_path: str = "artifacts/models/best.pt") -> None`
Loads neural surrogate weights, normalizer parameters, and static terrain into memory.

### `get_config() -> dict`
Returns the contents of `config.json`.

### `get_terrain() -> dict`
Returns:
```json
{
  "elevation": "[[float; 64]; 64]",
  "dx_m": 40.0,
  "bounds": [12.920, 77.560, 12.943, 77.583],
  "shape": [64, 64],
  "min_elevation": 81.2,
  "max_elevation": 100.0
}
```

### `forecast(params: dict) -> dict`
Input `params`:
```json
{
  "rain_intensity_mmhr": 80.0,
  "rain_duration_min": 45.0,
  "rain_shape": "constant",
  "drain_capacity_mmhr": 0.0,
  "horizon_steps": 120
}
```
Returns:
```json
{
  "times_s": "[int; 121]",
  "depth_frames": "[[[float; 64]; 64]; 121]",
  "rain_series_mmhr": "[float; 120]",
  "peak_depth_m": 1.452,
  "flooded_area_m2": 320000.0,
  "inference_time_ms": 38.5,
  "model_name": "unet-surrogate-v1"
}
```

### `run_solver(params: dict) -> dict`
Runs the ground-truth 2D Shallow Water Equations solver.
Returns matching shapes with additional key `"solve_time_s": float` and `"solver_name": str`.

---

## 4. HTTP API Endpoints

- `GET /health` -> `{"status": "ok", "model_loaded": bool, "is_mock": bool, "contract_version": "1.0"}`
- `GET /config` -> configuration JSON
- `GET /terrain` -> terrain elevation and bounds
- `GET /presets` -> list of predefined scenario parameters
- `POST /forecast` -> surrogate rollout
- `POST /compare` -> side-by-side surrogate and solver results with metrics

---

## 5. Formal Evaluation Metrics

Verification metrics comparing surrogate prediction $\hat{h}_{t,i,j}$ against solver ground truth $h_{t,i,j}$:

1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{T \cdot H \cdot W} \sum_{t=0}^{T} \sum_{i=1}^{H} \sum_{j=1}^{W} |\hat{h}_{t,i,j} - h_{t,i,j}| \quad [m]$$

2. **Root Mean Square Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{T \cdot H \cdot W} \sum_{t=0}^{T} \sum_{i=1}^{H} \sum_{j=1}^{W} (\hat{h}_{t,i,j} - h_{t,i,j})^2} \quad [m]$$

3. **Peak Depth Error**:
   $$\text{Error}_{\text{peak}} = |\max_{t,i,j}(\hat{h}_{t,i,j}) - \max_{t,i,j}(h_{t,i,j})| \quad [m]$$

4. **Inundation Intersection-over-Union (Wet IoU)**:
   $$\text{IoU} = \frac{|\hat{\mathcal{W}} \cap \mathcal{W}|}{|\hat{\mathcal{W}} \cup \mathcal{W}|}, \quad \text{where } \mathcal{W} = \{(i,j) \mid h_{T,i,j} \ge 0.05\text{ m}\}$$

5. **Relative Mass Balance Discrepancy**:
   $$\text{Error}_{\text{mass}} = \frac{|\sum_{i,j} \hat{h}_{T,i,j} - \sum_{i,j} h_{T,i,j}|}{\max(\sum_{i,j} h_{T,i,j}, 10^{-6})}$$

6. **Wetting Front Arrival Time Error**:
   $$\text{Error}_{\text{arrival}} = |t_{\text{arr}}(\hat{h}) - t_{\text{arr}}(h)| \quad [s]$$

7. **Speedup Factor**:
   $$\text{Speedup} = \frac{\text{Solver Runtime } [s]}{\text{Surrogate Inference Runtime } [s]}$$

