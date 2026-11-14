# HydroVision: Mass & Physics Accounting Specification

This document summarizes the mathematical verification of the water volume continuity equations on the conditioned 64×64 Marathahalli DEM ($\Delta x = 60.9\text{ m}$), ground-truthed on 30 training scenarios from the float32 dataset.

---

## 1. Domain & Volume Continuity Formulation

For a closed regular Cartesian domain with grid dimensions $H = 64, W = 64$ and cell resolution $\Delta x = 60.9\text{ m}$:
- Cell Area: $A_{cell} = \Delta x^2 = 3,708.81\text{ m}^2$
- Domain Area: $A_{domain} = 64 \times 64 \times A_{cell} = 15,191,285.76\text{ m}^2$
- Stored Volume at frame $t$: $V[t] = \sum_{r,c} h(t, r, c) \times A_{cell}\quad [m^3]$
- Rain Volume at step $t$: $V_{rain}[t] = \frac{R[t]}{1000 \times 3600} \times \Delta t \times A_{domain}\quad [m^3]$ ($\Delta t = 60\text{ s}$)

### (A) Per-Step Continuity Equation
$$V[t+1] - V[t] = V_{rain}[t] - \Delta V_{drain}[t]$$
where $\Delta V_{drain}[t] = \text{cum\_drain}[t+1] - \text{cum\_drain}[t]$.

### (B) 5-Step Bundled Window Continuity Equation ($k=5$)
$$V[t+5] - V[t] = \sum_{j=0}^{4} V_{rain}[t+j] - (\text{cum\_drain}[t+5] - \text{cum\_drain}[t])$$

---

## 2. Empirical Verification on Float32 Dataset

Across 30 diverse training scenarios ($3,600$ individual steps and $3,450$ 5-step windows):
- **Per-Step Budget Residual**: Mean = $4.80 \times 10^{-5}$, Max = $8.57 \times 10^{-3}$ (fraction of scenario rain volume)
- **5-Step Window Budget Residual**: Mean = $4.12 \times 10^{-5}$, Max = $1.10 \times 10^{-2}$

---

## 3. Ground-Truth-Free Formula Drainage Estimate

We evaluated the closed-form physical estimate that does not require ground-truth drainage targets:
$$\Delta V_{drain\_est}[t] = \sum_{r,c} \min\left(h(t, r, c) + d_{rain}[t],\; D_{mps} \cdot \Delta t\right) \times A_{cell}$$
where $d_{rain}[t] = \frac{R[t]}{1000 \times 3600} \times 60.0$ and $D_{mps} = \frac{\text{capacity}}{1000 \times 3600}$.

### Findings
- **Per-step error relative to true drain**: Mean = $0.62\%$, Max = $6.86\%$
- **Per-step error relative to total scenario rain**: Mean = $0.0005\%$, Max = $0.0081\%$
- **5-step window error relative to total scenario rain**: Mean = $0.0026\%$, Max = **$0.0377\%$**

---

## 4. Recommendation for Mass-Conservation Loss

**Recommendation**:
1. **Primary Choice**: Use the **True Window Drain** ($\text{cum\_drain}[t+5] - \text{cum\_drain}[t]$) from `drain_m3.npy` as the known physical sink during training. It is already stored with exact double-precision accounting in the dataset and introduces zero formulation error.
2. **Alternative Choice (Self-Consistent / Rollout Inference)**: The **Formula Estimate** has a worst-case error of **$0.0377\%$** (far below the $2.0\%$ threshold). It is suitable whenever ground-truth drainage series is not available (e.g. multi-step unrolled pushforward autoregressive training).
