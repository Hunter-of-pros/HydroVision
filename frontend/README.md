# HydroVision Frontend

Interactive web dashboard for real-time urban flood risk exploration, dynamic rainfall scenario manipulation, and hydrodynamic solver verification.

## Architecture & Technology Stack

- **Framework**: React 18+ with Vite (TypeScript)
- **Styling**: Tailwind CSS + Lucide Icons
- **Mapping & Spatial Visualization**: HTML5 Canvas raster overlay with bilinear depth colormap (sub-millisecond 60 FPS rendering)
- **State Management & Network**: Native React hooks + Typed REST API Client (`src/api.ts`)
- **Charting**: Responsive SVG precipitation hyetograph with active playback timeline cursor

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
Or from root:
```bash
make frontend-install
```

### 3. Start Local Development Server
```bash
npm run dev
```
Or from root:
```bash
make frontend-dev
```
The frontend will start at [http://localhost:5173](http://localhost:5173).

### 4. Build for Production
```bash
npm run build
```
Or from root:
```bash
make frontend-build
```

---

## Implemented UI Components

1. **Header Component (`Header.tsx`)**:
   - Branding, version tags, live backend health badge (`Mock Mode (Ready)` vs `Live Model`).
   - Real-time inference latency indicator (e.g. `38.5 ms`).
   - Active model name readout.

2. **Simulation Controls Panel (`Controls.tsx`)**:
   - **Predefined Storm Presets**: Moderate Summer Storm, Extreme Cloudburst, Engineered Drain Mitigation.
   - **Rainfall Intensity Slider**: $20 - 150\text{ mm/hr}$ with intensity categorizations.
   - **Storm Duration Slider**: $15 - 90\text{ minutes}$.
   - **Hyetograph Shape Toggles**: Constant, Triangular, Double Peak.
   - **Drain Infiltration Sink Slider**: $0 - 30\text{ mm/hr}$.
   - **Action Triggers**: "Run Neural Forecast" (fast surrogate rollout) and "Verify Against Solver" (side-by-side solver verification).

3. **Geospatial Canvas Map Viewer (`MapViewer.tsx`)**:
   - High-performance $64 \times 64$ raster canvas rendering with elevation contours and depth colormap.
   - Visual inundation gradient: dry ($< 0.05\text{m}$) $\rightarrow$ shallow puddle ($0.05 - 0.2\text{m}$) $\rightarrow$ street flood ($0.2 - 0.6\text{m}$) $\rightarrow$ severe flood ($> 1.0\text{m}$).
   - Interactive hover inspector reporting grid cell $[row, col]$, ground elevation ($z$), water depth ($h$), and water surface elevation ($z + h$).
   - North-up compass indicator and colormap legend scale.

4. **Global Playback Timeline (`Timeline.tsx`)**:
   - Play/pause simulation animation with smooth frame loop.
   - Time scrubber range slider spanning the full 2-hour horizon ($00:00:00$ to $02:00:00$).
   - Speed multipliers: $1\times$, $2\times$, $5\times$.
   - Live readouts of current timestamp, frame index, peak depth ($m$), and flooded surface area ($ha$).

5. **Precipitation Profile (`Hyetograph.tsx`)**:
   - Discrete rainfall intensity distribution over time with synchronized scrubber cursor.

6. **Hydrodynamic Solver Verification View (`ComparisonView.tsx`)**:
   - Dual synchronized side-by-side maps (Neural Surrogate vs. 2D Shallow Water Equations Solver).
   - Real-time metrics scorecard:
     - **Speedup Factor**: e.g. $39.5\times$ faster.
     - **Mean Absolute Error (MAE)**: Target $< 0.05\text{ m}$.
     - **Root Mean Square Error (RMSE)**: Target $< 0.10\text{ m}$.
     - **Inundation IoU (Critical Success Index)**: Extent overlap percentage.
     - **Peak Depth Discrepancy**: Difference in maximum ponding depth.
     - **Mass Conservation Error**: Relative volumetric balance discrepancy.
     - **Wetting Front Arrival Error**: Temporal lag in seconds.

