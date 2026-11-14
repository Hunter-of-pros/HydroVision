# HydroVision ML Handoff & Acceptance Guide

**Audience**: ML Pipeline Owner (Teammate)  
**Author**: Backend & Frontend Owner (Vikas)  
**Target**: Clean merge of trained model and numerical solver into HydroVision  

---

## 1. The Merge Condition: "Passes the Acceptance Script"

The backend and frontend are ready. To merge your ML code into `main` or `feature/backend-frontend`, your model must pass:
```bash
HYDRO_MODE=real python scripts/validate_model.py
pytest -v
```
When `validate_model.py` prints `>> ALL ACCEPTANCE CHECKS PASSED <<` and exits with code `0`, your code is certified ready for live frontend deployment.

---

## 2. Exact Input & Output Contracts

All functions in `hydrovision_ml/api.py` must obey these exact dimensions and units:

### Spatial & Temporal Dimensions
- **Grid Mesh**: $64 \times 64$ cells Cartesian grid. Row 0 = North, Column 0 = West.
- **Cell Resolution**: $dx = dy = 40.0\text{ meters}$. Catchment is $2.56 \times 2.56\text{ km}$.
- **Temporal Steps**: 120 intervals with $\Delta t = 60\text{ s}$. Total simulation time = 2 hours ($7200\text{ s}$).
- **Output Depth Frames**: Exactly **121 frames** ($t=0\text{ s}$ through $t=7200\text{ s}$).
  - Frame 0 ($t=0$) **must be identically 0.0 m everywhere** (dry initial terrain).
  - Shape: `(121, 64, 64)`.
  - Values: Water depth above ground in **meters ($m$)**, non-negative ($h \ge 0.0$), no NaNs, no Infs.
- **Rainfall Series**: List of **120 floats** in **mm/hr** (one precipitation value per 60s step).

### Input `params` Dictionary
```python
{
    "rain_intensity_mmhr": float,  # Peak rain [20.0, 150.0] mm/hr
    "rain_duration_min": float,    # Duration [15.0, 90.0] minutes
    "rain_shape": str,             # "constant" | "triangular" | "double_peak"
    "drain_capacity_mmhr": float,  # Urban sink infiltration [0.0, 30.0] mm/hr
    "horizon_steps": int,          # Default: 120 steps
}
```

### Return Dictionary for `forecast()` and `run_solver()`
```python
{
    "times_s": list[int],               # Length 121: [0, 60, 120, ..., 7200]
    "depth_frames": list[list[list]],   # 121 x 64 x 64 floats in meters
    "rain_series_mmhr": list[float],    # Length 120 in mm/hr
    "peak_depth_m": float,              # Maximum depth observed across all cells and frames
    "flooded_area_m2": float,           # Area exceeding 0.05m at final frame (wet_cells * 1600 m2)
    "inference_time_ms": float,         # Inference latency (< 2000 ms on CPU)
    "model_name": str,                  # e.g. "unet-surrogate-v1"
}
```

---

## 3. Recommended Implementation Order

1. **`hydrovision_ml/solver/swe_solver.py`**:
   - Implement the 2D local-inertial / de Almeida shallow water equations solver.
   - Closed domain boundary ($\mathbf{u} \cdot \mathbf{n} = 0$). Ensure strict mass conservation ($\text{residual} < 10^{-6}$).
2. **`hydrovision_ml/data/generate_dataset.py`**:
   - Sample diverse rainfall parameters (Latin Hypercube or uniform across ranges).
   - Run the solver to produce synthetic ground-truth trajectories and save to `artifacts/data/`.
3. **`hydrovision_ml/surrogate/train.py`**:
   - Train the 2D U-Net surrogate with physical mass loss and rollout loss.
   - Save the best checkpoint to `artifacts/models/best.pt`.
4. **`hydrovision_ml/surrogate/rollout.py` & `hydrovision_ml/api.py`**:
   - Wire `api.load_all()` to load `best.pt`.
   - Wire `api.forecast()` to run the fast PyTorch rollout and return the contract dictionary.
   - Wire `api.run_solver()` to call your solver.

---

## 4. The 3 Artifact Files Needed for Merge

Place these three artifacts in the repository before merging:
1. **`artifacts/models/best.pt`**: Trained PyTorch surrogate weights checkpoint.
2. **`artifacts/data/terrain.npz`**: Canonical $64 \times 64$ elevation array and geographic metadata.
3. **`results/eval_summary.json`**: Test dataset benchmark metrics (`mae`, `rmse`, `wet_iou`, `speedup`).

---

## 5. How to Validate Your Implementation

Run these two commands during development:
```bash
# 1. Run the formal model acceptance suite
HYDRO_MODE=real python scripts/validate_model.py --mode real

# 2. Run unit tests
pytest tests/ -v
```

> **Note on `tests/test_api_shapes.py`**:  
> The tests currently have `@pytest.mark.xfail(raises=NotImplementedError)`.  
> As you implement each function in `hydrovision_ml/api.py`, simply remove the `@pytest.mark.xfail` decorator from its corresponding test in `tests/test_api_shapes.py` to activate strict shape and bound assertions.

