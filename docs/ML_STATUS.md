# ML Pipeline Status — Phase 0 Audit
_Generated: 2026-11-14 by Phase 0 audit_

## 1. What Exists
- **Phase 1 (Terrain)**: `dem.py` with synthetic DEM, slope computation, persistence.
- **Phase 2 (Solver)**: `swe_solver.py` (2D local-inertial SWE, Manning n=0.035, CFL).
  `scenarios.py` with rain series (constant/triangular/double_peak) & LHS sampling.
- **Phase 3 (Data Gen)**: `generate_dataset.py` with 70/15/15 train/val/test splits.
- **Phase 6 (Metrics)**: `metrics.py` (MAE, RMSE, Peak Depth, Wet IoU, Mass Balance, Arrival).
- **Contract Wiring**: `api.py` connects terrain, solver, metrics, and model info.

## 2. What Is Missing
- **Phase 4 (Neural Surrogate)**: `UNetSurrogate`, `Normalizer`, AR rollout loop.
  `forecast()` and `forecast_batch()` raise `NotImplementedError`.
- **Phase 5 (Training)**: Loss functions, physics penalty, data loaders, training script.
- **Artifacts**: `artifacts/models/best.pt` and `normalizer.json` not yet generated.

## 3. Contradictions & Audit Findings
1. **Stale xfail markers**: `test_api_shapes.py` marks `get_terrain`, `run_solver`,
   `compute_metrics`, `get_model_info` as xfail, but all 4 now XPASS. Only `forecast` xfails.
2. **`load_all()` stub**: Accepts `model_path` but only loads terrain; model loading missing.
3. **`get_model_info()`**: Returns `parameters_count: 0` until model checkpoint exists.
4. **Boundary Condition**: Solver has open boundaries at domain edges; bucket tests
   require accounting for zero-gradient/closed boundary assumptions.
5. **Ignore Rules**: `.gitignore` was excluding `artifacts/data/*.npz`, needing explicit
   exception for `terrain.npz`.
