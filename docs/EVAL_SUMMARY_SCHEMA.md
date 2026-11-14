# Evaluation Summary Schema (`eval_summary.json`)

**Specification Target**: `results/eval_summary.json`  
**Schema Definition**: [docs/eval_summary.schema.json](file:///Users/apple/Desktop/hydrovision/docs/eval_summary.schema.json)  
**Consumer**: Backend (`GET /results`) and Frontend (`EvaluationTab`)  
**Owner**: ML Pipeline (Producer) / Backend & Frontend (Consumer)  

---

## 1. Purpose

The HydroVision problem statement (PS 1.2) specifically requires empirical evidence of:
1. **Physical Conservation**: Does penalizing physics loss prevent water loss/creation?
2. **Autoregressive Stability**: Does rollout training prevent error compounding over 120 steps?
3. **Speedup Scaling**: How does inference speed compare to 2D SWE solvers as grid dimension scales?

The file `results/eval_summary.json` aggregates these benchmark metrics. When absent, the backend falls back to `results/eval_summary.mock.json` with `is_mock: true`.

---

## 2. Field Specifications

| Field | Type | Required | Description |
|---|---|---|---|
| `generated_at` | `string` (ISO 8601) | Yes | UTC timestamp of benchmark evaluation. |
| `hardware` | `string` | Yes | Device and compute environment (e.g., `"NVIDIA RTX 4090 (24GB) / Intel Core i9-13900K"`). |
| `is_mock` | `boolean` | Yes | `false` for genuine evaluation metrics; `true` for mock / synthetic data. |
| `test_set` | `object` | Yes | Description of test suite (`n_runs`: int, `rain_range_mmhr`: `[min, max]`). |
| `ablation` | `list[object]` | Yes | Performance comparison across 3 core model variants (defined below). |
| `error_vs_horizon` | `object` | Yes | Rollout error accumulation (`steps`: `list[int]`, `mae_m`: `list[float]`). |
| `speedup_scaling` | `list[object]` | Yes | Runtime scaling across grid sizes (`grid`: str, `solver_s`: float, `surrogate_ms`: float). |

---

## 3. Required Ablation Study Configurations

The `ablation` list must contain entries for the three canonical training configurations:

1. **`"A plain"`**: Standard data-driven U-Net trained purely with supervised $\mathcal{L}_2$ / MSE loss.
2. **`"B mass loss"`**: U-Net trained with supervised MSE loss + physical mass conservation constraint penalty ($\lambda_{\text{mass}} \mathcal{L}_{\text{mass}}$).
3. **`"C mass loss + rollout training"`**: Full HydroVision architecture with mass loss + pushforward / multi-step rollout fine-tuning for error attenuation.

Each ablation item must report:
- `name`: One of the 3 names above.
- `mae_m`: Mean Absolute Error across test set in meters.
- `rmse_m`: Root Mean Squared Error across test set in meters.
- `wet_iou`: Inundation extent Intersection-over-Union ($\ge 0.05\text{ m}$).
- `mass_residual_max`: Maximum relative domain water balance residual.

---

## 4. Reference JSON Example

```json
{
  "generated_at": "2026-11-14T12:00:00Z",
  "hardware": "NVIDIA GeForce RTX 4090 / AMD Ryzen 9 7950X",
  "is_mock": false,
  "test_set": {
    "n_runs": 50,
    "rain_range_mmhr": [20.0, 150.0]
  },
  "ablation": [
    {
      "name": "A plain",
      "mae_m": 0.082,
      "rmse_m": 0.124,
      "wet_iou": 0.621,
      "mass_residual_max": 0.184
    },
    {
      "name": "B mass loss",
      "mae_m": 0.051,
      "rmse_m": 0.078,
      "wet_iou": 0.743,
      "mass_residual_max": 0.038
    },
    {
      "name": "C mass loss + rollout training",
      "mae_m": 0.024,
      "rmse_m": 0.039,
      "wet_iou": 0.865,
      "mass_residual_max": 0.012
    }
  ],
  "error_vs_horizon": {
    "steps": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
    "mae_m": [0.005, 0.008, 0.012, 0.015, 0.018, 0.021, 0.023, 0.024, 0.025, 0.025, 0.026, 0.026]
  },
  "speedup_scaling": [
    {
      "grid": "32x32",
      "solver_s": 0.38,
      "surrogate_ms": 12.0
    },
    {
      "grid": "64x64",
      "solver_s": 1.52,
      "surrogate_ms": 38.5
    },
    {
      "grid": "128x128",
      "solver_s": 8.40,
      "surrogate_ms": 112.0
    },
    {
      "grid": "256x256",
      "solver_s": 46.20,
      "surrogate_ms": 340.0
    }
  ]
}
```
