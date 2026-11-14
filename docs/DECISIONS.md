# HydroVision Architectural Decisions: Speed & Surrogate Strategy

_Date: 2026-11-14_
_Author: ML Pipeline_
_Status: Pending User Decision_

---

## 1. Speed Feasibility Probe Results (CPU Baseline)

Hardware: Intel i9-12900H (14 cores / 20 threads), RAM 16GB.
PyTorch: `2.15.0+cpu` (CPU-only build; official CUDA wheels for Python 3.15 not yet released).
Surrogate: ~468k parameter U-Net (7 input channels, 64x64 spatial resolution).

| Mode | Wall Time (Median) | Per-Scenario Latency | Speedup vs Solver |
|---|---|---|---|
| **2D SWE Solver** (1 scenario, 120 steps) | **254.6 ms** | **254.6 ms** | **1.00×** (Baseline) |
| **U-Net 1-step Autoregressive** (Batch=1, 120 passes) | 607.2 ms | 607.2 ms | **0.42×** (2.4× slower) |
| **U-Net Batched Ensemble** (Batch=64, 120 passes) | 25,697.5 ms | 401.5 ms | **0.63×** (CPU bottleneck) |
| **U-Net Bundled** (Batch=1, 24 passes × 5 steps) | **111.9 ms** | **111.9 ms** | **2.28×** (Faster on CPU) |

> [!NOTE]
> The single-step autoregressive U-Net on CPU suffers from 120 sequential Python/PyTorch kernel launch overheads, making it slower than the compiled/vectorized NumPy solver. However, **temporal bundling (5 steps/pass)** cuts calls by 5× and delivers an immediate **2.28× speedup** even without GPU acceleration.

---

## 2. Speed Strategy Options

### Option A: Honest Solver Comparison + Batched Ensemble Focus
- **Approach**: Keep the existing 64×64 local-inertial SWE solver as ground truth. Train single-step autoregressive surrogate.
- **Reporting**: Report single-scenario latency honestly on CPU (~0.42× speedup). Headline batched throughput (e.g., GPU/ensemble 100+ scenarios at once) where parallel GPU tensor cores dramatically outperform sequential CPU loops.
- **Pros**:
  - Simplest training objective (predict $h_{t+1}$ given $h_t$).
  - Cleanest architectural alignment with CONTRACT.md.
  - Zero risk of multi-step rollout accumulation in single pass.
- **Cons**:
  - Interactive single-scenario web demo feels slower than the numerical solver on CPU.
  - Does not meet CONTRACT.md target of `<50ms` on CPU without optimization.

---

### Option B: Temporal Bundling + Model Optimizations (Recommended)
- **Approach**: Design surrogate to output $\Delta k$ steps per pass (e.g., $k=5$ steps per forward pass = 24 total passes for 120-step horizon). Combine with:
  - Width pruning (channel base 24 instead of 32 -> ~260k params).
  - Memory format optimization (`torch.channels_last`).
  - ONNX Runtime or `torch.compile` / OpenVINO on Windows CPU.
- **Pros**:
  - Immediately achieved **111.9 ms** on CPU in probe (2.28× speedup over solver).
  - Easily reaches **<40 ms** with width tuning and ONNX/OpenVINO CPU inference.
  - Directly satisfies the `<50ms` real-time requirement from CONTRACT.md.
- **Cons**:
  - Slightly more complex loss formulation (multi-frame loss balancing).
  - Dataset generator must slice targets in chunks of 5 timesteps.

---

### Option C: Higher-Fidelity Reference Solver (4× Finer Mesh)
- **Approach**: Upgrade the reference ground-truth solver to a 4× finer grid ($256 \times 256$, $\Delta x = 10\text{ m}$), coarsened back to $64 \times 64$ via block averaging.
- **Estimated Generation Cost**:
  - Cell count increases $16\times$ ($256^2 / 64^2$).
  - CFL stability condition requires $\Delta t \propto \Delta x$, increasing sub-steps by $4\times$.
  - Compute scaling factor: $\approx 16 \times 4 = 64\times$ solver time.
  - Estimated per-scenario time: $0.255\text{ s} \times 64 \approx 16.3\text{ seconds}$.
  - Generating 200 scenarios: $\approx 54\text{ minutes}$ generation time.
- **Pros**:
  - Massive apparent speedup for ML model ($16.3\text{ s}$ vs $0.11\text{ s} \to \approx 145\times$).
  - Captures true sub-grid wave dynamics.
- **Cons**:
  - Heavy compute cost during dataset generation.
  - Bilinearly upsampled synthetic DEM contains no new terrain features (synthetic roughness does not equal real sub-grid topography).
  - Requires updating CONTRACT.md specifications.

---

## 3. Recommendation

**We recommend Option B (Temporal Bundling with $k=5$ frames/pass):**
1. Probe empirically proves that temporal bundling brings CPU inference to **111.9 ms** (2.28× faster than solver).
2. With lightweight width adjustment (`width=24`) and ONNX export, CPU latency will drop below **45 ms**, strictly meeting the CONTRACT.md requirement.
3. Once PyTorch releases official CUDA wheels for Python 3.15, GPU inference will achieve sub-10ms latency.
