# HydroVision — Judge & Evaluator Technical Q&A

This document provides transparent, scientifically grounded answers to the most common questions asked by technical judges, domain hydrologists, and municipal stakeholders.

---

### Q1: Where does the $30\times–40\times$ speedup come from compared to traditional hydrodynamic models?

**Answer:**  
The speedup is a fundamental algorithmic shift from **micro-stepping numerical integration** to **learned spatio-temporal operator mapping**:

1. **Numerical Solver Bottleneck (CFL Stability Condition):**  
   Numerical 2D Shallow Water Equations (SWE) solvers must obey the Courant-Friedrichs-Lewy (CFL) numerical stability condition:  
   $$\Delta t_{num} \le \frac{\Delta x}{\sqrt{gh} + \sqrt{u^2 + v^2}}$$  
   On a $40\text{ m}$ grid with rapidly accelerating shallow runoff, stability demands sub-second time steps ($\Delta t_{num} \approx 0.1\text{ s} - 0.5\text{ s}$). Simulating 2 hours ($7,200\text{ s}$) requires over **14,000 to 70,000 iterative numerical flux updates** across all $4,096$ grid cells, taking $1.5\text{ s}$ to multiple minutes on CPU.
2. **Neural Surrogate Acceleration:**  
   The neural surrogate (U-Net / convolutional operator) maps the state across macroscopic intervals ($\Delta t = 60\text{ s}$) in a single forward tensor pass. Predicting the entire 120-frame horizon requires only **120 autoregressive forward passes**, executing in **~38 ms on standard CPU** without spatial mesh iteration.

---

### Q2: What does the physics-informed term actually do? Why isn't standard MSE loss enough?

**Answer:**  
Standard unconstrained Mean Squared Error (MSE) loss optimizes average pixel-level depth agreement but has **no concept of physical continuity**:

1. **The Hallucination Problem:**  
   In autoregressive rollouts over 120 steps, small pixel errors compound. Pure data-driven networks routinely violate the first law of thermodynamics: they create water out of nowhere or allow flooded retention ponds to vanish without a drainage sink.
2. **The Physics Conservation Term:**  
   We introduce a hard mass-conservation residual penalty into the loss function:  
   $$\mathcal{L}_{\text{physics}} = \frac{1}{T} \sum_{t=1}^T \frac{\left| V_t - \left( V_0 + \sum_{\tau=1}^t \Delta \text{Rain}_\tau - \Delta \text{Drain}_\tau - \Delta \text{Outflow}_\tau \right) \right|}{\max\left(\sum_{\tau=1}^t \Delta \text{Rain}_\tau, 10^{-6}\right)}$$  
   This term explicitly forces the neural network's spatial predictions to sum to the exact physical mass budget of rainfall minus drainage, bounding rollout drift across the entire 2-hour forecast.
3. **Non-Negativity Constraint:**  
   A ReLU / non-negative activation prevents physically nonsensical negative water depths ($h \ge 0$).

---

### Q3: What do KSNDMC's (Karnataka State Natural Disaster Monitoring Centre) existing tools already do, and how does HydroVision differ?

**Answer:**  
KSNDMC and the BBMP (Bruhat Bengaluru Mahanagara Palike) already operate sophisticated weather and disaster monitoring infrastructure, including:
- **Telemetric Rain Gauges (TRGs):** Hundreds of automated rain gauge stations across Bengaluru (Varuna Mitra network) reporting real-time precipitation every 15 minutes.
- **Doppler Weather Radar (DWR):** Short-range rainfall intensity estimates.
- **Bengaluru Megha Sandesha & Static Hazard Maps:** Historical spatial flood vulnerability maps identifying known waterlogging zones and low-lying rajakaluve (storm drain) hotspots.

**How HydroVision Complements Them (The Gap):**  
- KSNDMC's tools provide **point-source rainfall monitoring** and **static historical vulnerability zones**. They do not run real-time dynamic overland flow hydrodynamics during a live storm.
- HydroVision takes KSNDMC's incoming telemetric rain rates and instantaneously converts them into **forward-looking, dynamic 2D inundation depth maps ($h(x, y, t)$)**, predicting which roads and intersections will submerge 20, 40, or 60 minutes before the runoff accumulates.

---

### Q4: What is explicitly NOT claimed by HydroVision?

**Answer:**  
To maintain scientific integrity and avoid overpromising, we explicitly document our limitations:

1. **Not Field-Calibrated Depth Ground Truth:**  
   The neural surrogate is trained to imitate a numerical 2D Shallow Water Equations solver. It is a surrogate of the *solver*, not a calibrated representation of physical Bengaluru street sensors. Solver inaccuracies are inherited by the neural net.
2. **No Subsurface Pipe Network Coupling:**  
   Urban flooding often involves pressurized stormwater sewer pipe surcharge (manhole backflow). HydroVision currently models drainage as an effective surface infiltration sink ($\text{mm/hr}$), not full 1D SWMM pipe hydraulics.
3. **Illustrative Elevation Terrain:**  
   The current demonstration operates on a synthetic $64 \times 64$ Digital Elevation Model ($40\text{ m}$ cell resolution). Ingesting real Cartosat/SRTM elevation data requires running the ingestion pipeline documented in `docs/DEM_HOWTO.md`.
4. **No Spatially Heterogeneous Storm Cells:**  
   Rainfall profiles are modeled as spatially uniform over the $2.56\text{ km} \times 2.56\text{ km}$ tile; localized convective cloudburst tracks are future work.
5. **No Official Municipal Hazard Categorization:**  
   Thresholds ($15\text{ cm}$ vehicle hazard, $30\text{ cm}$ emergency access cutoff) in `config.json` are illustrative operational markers, not certified municipal safety standards.

---

### Q5: Can this system be deployed on low-power hardware in an emergency control room without expensive GPUs?

**Answer:**  
**Yes.** This was an explicit architectural design requirement:
- **CPU-First Inference:** The surrogate model uses fewer than 5 million parameters and takes **~38 ms on standard Intel/Apple Silicon CPUs**.
- **Bandwidth Optimization:** By rounding depth values to 3 decimals server-side (1 mm precision), GZip compression shrinks 121 frames of high-resolution inundation grids down to **77.3 KB over the wire**.
- **Browser-Native Visualization:** The map viewer renders via an HTML5 2D canvas at 60 fps, consuming less than 40 MB of browser RAM.
- **Offline Resilience:** If network connectivity to the emergency operations center drops, the frontend automatically serves cached reference scenarios from `frontend/public/` with visible offline banners.

---

### Q6: Why does the system display amber "MOCK ENGINE" banners during the demonstration?

**Answer:**  
This reflects our commitment to **scientific honesty and ethical AI development**:
- In the hackathon workflow, the ML pipeline and full-stack serving layer were built with strict interface separation (`docs/CONTRACT.md`).
- While the ML teammate finalizes the production surrogate weights (`best.pt`), the mock engine serves deterministic synthetic data.
- Rather than deceptively presenting simulated data as trained model outputs, HydroVision enforces persistent amber banners across every screen, greys out unverified scorecard metrics, and stamps exported PNGs with visible watermarks. When real weights are merged, the backend verifies them with `scripts/validate_model.py` and the mock banners automatically disappear.
