# HydroVision Hackathon Demonstration Script

A step-by-step presentation outline for judging rounds and live demonstrations.

---

## 1. 30-Second Hook & Problem Statement
- **Hook**: "When a cloudburst strikes a dense city, municipal emergency managers have zero minutes to waste—yet traditional flood simulators take hours to calculate where the water will pool."
- **Solution**: "HydroVision is a physics-informed neural surrogate that predicts 2 hours of urban street flooding in less than 50 milliseconds—right inside a browser map, while proving its accuracy against a full hydrodynamic solver."

---

## 2. Interactive Rainfall Slider Walkthrough
- Open browser at `http://localhost:5173`.
- Point out the $2.56\text{ km} \times 2.56\text{ km}$ urban elevation grid and natural drainage channels.
- Select preset: **Moderate Summer Storm** ($60\text{ mm/hr}$ for 45 min).
- Drag the **Rainfall Intensity Slider** up to $120\text{ mm/hr}$—highlight sub-second map updates.
- Scrub the time slider from minute 0 to minute 120 to show water accumulating in low-lying retention basins.

---

## 3. "Verify Against Solver" Side-by-Side Comparison
- Click the **"Verify Against Solver"** button.
- Note the solver timer spinning for 1.5 seconds (representing heavy numerical computation).
- Show side-by-side maps: Neural Surrogate vs. 2D Shallow Water Equations Solver.
- Highlight visual agreement in flood extents and depth contours.

---

## 4. Physics-Informed Metrics & Edge Footprint
- Walk through the Scorecard:
  - **Mean Absolute Error**: < 0.05 m across all cells
  - **Wet IoU**: Over 85% overlap of inundated streets
  - **Mass Balance Error**: Near-zero discrepancy enforced by physics loss
  - **Speedup**: Over 30x faster than the numerical solver
- Emphasize lightweight deployment: CPU-only, no GPU required, runs on laptop or edge server.

---

## 5. Summary & Next Steps
- Explain roadmap: integrating real municipal storm pipe GIS layers and live Doppler radar data.
- Conclude: "HydroVision makes flood forecasting instant, accurate, and accessible."

