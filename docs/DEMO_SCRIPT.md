# HydroVision — 3-Minute Live Hackathon Demonstration Script

This rehearsal-ready script provides a structured, time-stamped 3-minute walkthrough for hackathon judging panels, followed by an **"If Something Breaks"** contingency reference.

---

## ⏱️ 3-Minute Presentation Timeline

### [0:00 – 0:30] Hook & Problem Statement (PS 1.2)
- **Speaker**:  
  *"When a cloudburst strikes a dense city, emergency responders cannot wait hours for heavy numerical fluid dynamics simulations to compute street water levels. Traditional 2D Shallow Water Equations solvers take minutes or hours, forcing cities into reactive flood responses."*
- **Action**:  
  Open [http://localhost:5173](http://localhost:5173). Show the clean dashboard.
- **Key Message**:  
  *"HydroVision is an edge-ready, physics-informed neural surrogate. It delivers 2 hours of spatial flood predictions across a 2.5 km catchment in **38 milliseconds on CPU**, while proving its physical accuracy against a numerical hydrodynamic solver."*

---

### [0:30 – 1:15] Interactive Map Exploration & Local Probe
- **Action**:  
  1. Select the **"Moderate Summer Storm"** preset ($60\text{ mm/h}$, 45 min).
  2. Point out the top header latency metrics: **Model: ~38ms** alongside **E2E: ~55ms**. Hover over the latency badge to reveal the breakdown tooltip.
  3. Drag the **Peak Rainfall Intensity** slider up to $100\text{ mm/h}$. Point out the **300ms debounce** that updates the map without lag.
  4. Scrub the **Global Timeline** from $0\text{ s}$ to $7200\text{ s}$ (2 hours) to show water accumulating in natural drainage basins.
  5. Click any street intersection on the canvas to drop a **Probe Pin**.
- **Speaker**:  
  *"Notice the localized depth hydrograph below. An emergency planner can inspect any street corner to observe exact flood arrival time (+18 min) and peak inundation depth (1.42 m). Above, our illustrative hazard levels indicate wetted areas and thresholds without making unvalidated municipal claims."*

---

### [1:15 – 1:55] "What-If" Interventions & Run Comparison Drawer
- **Speaker**:  
  *"Municipal planning requires testing interventions. What if we invest in engineered retention drains?"*
- **Action**:  
  1. Click **"Save Current Run"** (auto-saves as `"Run A: 100 mm/h, drain 0"`).
  2. Adjust **Drain Infiltration Sink** slider to $20\text{ mm/h}$.
  3. Click **"Save Current Run"** (auto-saves as `"Run B: 100 mm/h, drain 20"`).
  4. Open the **History** drawer. Select both **Run A** and **Run B**, then click **"Compare 2 Runs Side-by-Side"**.
- **Point to the Screen**:  
  1. Highlight the **Delta Impact Panel**:
     - $\Delta \text{Peak Depth}: -0.312\text{ m}$ (*Mitigated*)
     - $\Delta \text{Flooded Area}: -14.2\text{ ha}$ (*Reduced*)
     - $\Delta \text{Total Volume}: -38,500\text{ m}^3$ (*Drained*)
  2. Scrub the shared timeline: both maps animate in synchronized lockstep using the same color scale.
  3. Click **X** to exit comparison mode.

---

### [1:55 – 2:30] Solver Verification & Evaluation Tab
- **Action**:  
  1. Click **"Verify Against Solver"**.
  2. Note the solver progress spinner executing the numerical ground truth (~1.5s).
  3. Highlight the **7-Metric Scorecard**:
     - Mean Absolute Error ($< 0.05\text{ m}$)
     - Wet Cell Extent IoU ($> 85\%$)
     - Mass Conservation Discrepancy ($< 0.002$)
     - Speedup factor ($> 30\times$ faster on CPU)
  4. Click the **"Evaluation Tab"** in the top navigation.
- **Speaker**:  
  *"Our Evaluation Tab proves physical stability across the entire 2-hour rollout: the Error vs. Horizon curve shows errors stay bounded, and our Mass Residual curve proves that the physics-informed loss prevents the neural surrogate from hallucinating or losing water."*

---

### [2:30 – 3:00] Honesty, Edge Footprint & Conclusion
- **Speaker**:  
  *"HydroVision is lightweight and edge-first: it requires no GPU, serializes 3-decimal payloads in under 80 KB over GZip, and is built for deployment on low-cost edge servers or municipal laptops.*  
  *We are completely honest about what is modeled: our mock mode carries visible disclaimers, the terrain is marked as illustrative, and the surrogate is trained to imitate a 2D Shallow Water Equations solver.*  
  *HydroVision transforms urban flood forecasting from reactive aftermath reporting into proactive, instantaneous intelligence."*

---

## 🛠️ "If Something Breaks" Contingency Reference

| Scenario | What Happens | What To Do / Say to Judges |
|---|---|---|
| **Backend Crashes or Stops** | The frontend automatically catches network failures and switches to `/forecast_fixture.json` and `/compare_fixture.json`. | An amber banner appears: `OFFLINE FALLBACK: saved example, not a live forecast`. Explain: *"HydroVision includes full client-side demo resilience. If municipal connectivity drops, cached reference scenarios remain operational."* |
| **Invalid Parameters (422 Error)** | The backend rejects inputs outside `config.json` and returns a clean 422 message. | A red error card appears with **"Reset Defaults"** and **"Retry Request"** buttons. Click **"Reset Defaults"** to restore valid parameters in one click. |
| **Saved Runs Lose Frames on Page Refresh** | Numerical frames are omitted from `localStorage` to respect the 5MB browser quota. The drawer displays `Frames cleared on reload`. | Click **"Re-run to restore"** on the run card. Explain: *"We deliberately keep localStorage bounded; clicking re-run regenerates the 121 frames in under 40 milliseconds."* |
| **Real Model Mode (`HYDRO_MODE=real`) Missing Weights** | The backend returns `status: "degraded"` on `/health` and HTTP 503 on `/forecast`. | Explain: *"Unlike deceptive prototypes that silently fake mock output, HydroVision strictly refuses to serve fake data under real mode, returning an explicit 503."* |
| **Accidental Double Click on Run Button** | `AbortController` automatically cancels the in-flight request. | No duplicates or race conditions occur. The console quietly cancels the stale request and fulfills the latest one. |
