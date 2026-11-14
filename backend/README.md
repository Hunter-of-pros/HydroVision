# HydroVision Backend

FastAPI service exposing neural surrogate flood forecasts and numerical solver verification to the frontend map UI.

## Responsibilities & Boundaries

- **Owner**: Backend Developer (Vikas)
- **Boundary**: Imports **only** `hydrovision_ml`. Never imports raw solver internals or internal PyTorch files directly.
- **Contract**: All payloads strictly adhere to [`docs/CONTRACT.md`](../docs/CONTRACT.md).

---

## Getting Started

### 1. Prerequisites
Ensure the root virtual environment is activated:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run with Mock (Default for frontend development)
In mock mode, the service serves synthetic 64x64 DEM and mock predictions without needing GPU or trained PyTorch weights:
```bash
HYDRO_MODE=mock uvicorn backend.app:app --reload --port 8000
```
Or via Makefile:
```bash
make mock-backend
```

### 3. Run with Real ML Models
Once the ML teammate finishes Phase 4 and exports `artifacts/models/best.pt`:
```bash
HYDRO_MODE=real uvicorn backend.app:app --reload --port 8000
```
Or via Makefile:
```bash
make real-backend
```

---

## Endpoints

| Method | Route | Status | Description |
|---|---|---|---|
| `GET` | `/health` | Working | Returns `{"status": "ok", "model_loaded": true, "is_mock": true, "contract_version": "1.0"}` |
| `GET` | `/config` | Working | Returns contents of `config.json` |
| `GET` | `/terrain` | Working (via mock) | Returns 64x64 elevation grid and geographic bounds |
| `GET` | `/presets` | Working (via mock) | Predefined storm scenarios for slider presets |
| `POST` | `/forecast` | 501 (Phase 7) | Fast neural surrogate rollout (121 frames x 64 x 64) |
| `POST` | `/compare` | 501 (Phase 7) | Side-by-side surrogate vs SWE solver verification |

---

## Interactive API Docs
When running locally, explore the interactive Swagger documentation at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

