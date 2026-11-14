# HydroVision Frontend

Interactive web dashboard for real-time urban flood risk exploration, dynamic rainfall scenario manipulation, and solver verification.

## Architecture & Technology Stack

- **Framework**: React 18+ with Vite (TypeScript)
- **Styling**: Tailwind CSS + Lucide Icons + Radix UI / Shadcn UI
- **Mapping & Spatial Visualization**: Leaflet / React-Leaflet with Canvas tile layer or Heatmap overlay
- **State Management & Querying**: TanStack React Query + Zustand
- **Charting**: Recharts (for rainfall hyetographs and point depth hydrographs)

## Ownership & Interface Boundary

- **Owner**: Frontend Developer (Vikas)
- **Boundary**: Talks **ONLY** to the FastAPI backend via HTTP REST endpoints (`VITE_API_URL`). Never imports or references Python code or ML artifacts directly.
- **Contract Reference**: [`docs/CONTRACT.md`](../docs/CONTRACT.md)

---

## Setup & Local Development

### 1. Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```
Ensure `VITE_API_URL` points to your backend instance (default: `http://localhost:8000`).

### 2. Install Dependencies
```bash
npm install
```

### 3. Start Local Development Server
```bash
npm run dev
```
The frontend will start at [http://localhost:5173](http://localhost:5173).

---

## Planned UI Components (Phase 8)

1. **Interactive Geospatial Map**:
   - Leaflet base map centered on the target urban catchment bounds from `GET /terrain`.
   - Semi-transparent depth overlay layer (colormap: blue gradient for water depth > 0.05m).
   - Time scrubber slider (frame 0 to 120, displaying elapsed time `00:00` to `02:00` hours).

2. **Rainfall & Drainage Control Panel**:
   - `rain_intensity_mmhr` slider: 20 to 150 mm/hr
   - `rain_duration_min` slider: 15 to 90 minutes
   - `rain_shape` radio toggle: Constant, Triangular, Double Peak
   - `drain_capacity_mmhr` slider: 0 to 30 mm/hr
   - Quick preset selector buttons (Summer Storm, Cloudburst, Engineered Drain).

3. **Verification & Solver Comparison View**:
   - "Verify Against Solver" trigger button (`POST /compare`).
   - Side-by-side synchronized map comparison (Surrogate vs 2D SWE Solver).
   - Real-time metrics scorecard: MAE, Peak Depth Error, Inundation IoU, and Speedup factor.

