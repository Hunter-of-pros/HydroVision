# HydroVision Interface Contract v1.1 Proposal

**Status**: PROPOSAL (Non-binding discussion document for ML Teammate)  
**Author**: Backend / Frontend Owner (Vikas)  
**Date**: November 2026  
**Target Specification**: Contract v1.1 (Additive extension to Contract v1.0)  

---

## 1. Motivation & Background

In Contract v1.0, Metric 5 is defined as:
$$\text{Error}_{\text{mass}} = \frac{|\sum_{i,j} \hat{h}_{T,i,j} - \sum_{i,j} h_{T,i,j}|}{\max(\sum_{i,j} h_{T,i,j}, 10^{-6})}$$

While valuable, this metric **measures surrogate-to-solver agreement at final horizon $T=120$**, not physical mass conservation. If the numerical solver or surrogate both leak water or create phantom mass, Metric 5 can still be near zero despite severe physical violation.

To provide rigorous evidence of **physics-informed conservation and temporal numerical stability** (crucial for hackathon judges and domain hydrologists), we propose Contract v1.1.

### Key Principles of v1.1
1. **Strict Non-Breaking Additivity**: All Contract v1.0 keys, units, shapes ($64 \times 64$, 121 frames), and the 7 original metrics remain 100% intact. Existing v1.0 clients and tests continue to work without modification.
2. **True Mass-Budget Tracking**: We track the full physical water balance equation at every single frame $t \in [0, 120]$:
   $$V(t) = V_{\text{initial}} + V_{\text{rain}}(t) - V_{\text{drain}}(t) - V_{\text{outflow}}(t)$$
3. **Temporal Stability Evidence**: Per-frame error series allow detecting error explosion, numerical dispersion, or high-frequency rollout instability.

---

## 2. Proposed Additive Fields

### 2.1 Responses for `forecast()` and `run_solver()`

Four new series tracking the domain-wide water balance over time (each a list of 121 floats, corresponding to $t = 0, 60, 120, \dots, 7200\text{ s}$):

| Field Name | Type | Physical Unit | Description |
|---|---|---|---|
| `volume_m3_series` | `list[float]` (len 121) | $m^3$ | Total ponded water volume on the grid: $V_t = \sum_{r=0}^{63} \sum_{c=0}^{63} h_{t,r,c} \cdot dx \cdot dy$, where $dx = dy = 40.0\text{ m}$. |
| `cum_rain_m3_series` | `list[float]` (len 121) | $m^3$ | Total cumulative precipitation volume deposited onto the catchment up to time $t$. ($0.0$ at $t=0$). |
| `cum_drain_m3_series` | `list[float]` (len 121) | $m^3$ | Total cumulative drainage/infiltration volume removed by urban sinks up to time $t$. ($0.0$ at $t=0$). |
| `cum_outflow_m3_series` | `list[float]` (len 121) | $m^3$ | Total cumulative water volume exiting past the domain boundaries up to time $t$. ($0.0$ at $t=0$). |
| `mass_residual_series` | `list[float]` (len 121) | dimensionless | Normalized mass balance residual over time (defined in Section 2.2). |

#### Mathematical Consistency
At every time frame $t$:
$$\text{Expected Volume } V_{\text{expected}}(t) = V_{\text{initial}} + \text{cum\_rain}(t) - \text{cum\_drain}(t) - \text{cum\_outflow}(t)$$
Since the catchment starts dry at $t=0$, $V_{\text{initial}} \equiv 0.0\text{ m}^3$.

---

### 2.2 Additions to Formal Evaluation Metrics (`compute_metrics()`)

The existing 7 scalar metrics are preserved. Metric 5 remains documented as the **Final-Horizon Discrepancy** between surrogate and solver. 

We add three new fields to `compute_metrics()`:

#### 1. Per-Frame Mean Absolute Error Series (`mae_series`)
- **Type**: `list[float]` of length 121 ($m$).
- **Definition**:
  $$\text{mae\_series}[t] = \frac{1}{64 \times 64} \sum_{r=0}^{63} \sum_{c=0}^{63} |\hat{h}_{t,r,c} - h_{t,r,c}|$$
- **Purpose**: Demonstrates whether surrogate rollout errors accumulate monotonically or stay bounded over the 2-hour forecast horizon.

#### 2. Mass Conservation Residual Series (`mass_residual_series`)
- **Type**: `list[float]` of length 121 (dimensionless).
- **Definition**:
  $$\text{residual}(t) = \begin{cases} 0.0 & \text{if } t = 0 \\ \frac{|V_t - (\text{cum\_rain}_t - \text{cum\_drain}_t - \text{cum\_outflow}_t)|}{\max(\text{cum\_rain}_t, 10^{-6})} & \text{if } t > 0 \end{cases}$$
- **Surrogate vs. Solver**:
  - `metrics["mass_residual_series"]` evaluates the surrogate's mass conservation over time.
  - `metrics["solver_mass_residual_series"]` evaluates the numerical solver's conservation (which should strictly satisfy $\text{residual} < 10^{-6}$ in mass-conservative finite volume formulations).

#### 3. Peak Inundation Envelope IoU (`peak_extent_iou`)
- **Type**: `float` $\in [0.0, 1.0]$.
- **Definition**:
  $$\text{peak\_extent\_iou} = \frac{|\hat{\mathcal{E}} \cap \mathcal{E}|}{|\hat{\mathcal{E}} \cup \mathcal{E}|}$$
  where $\mathcal{E} = \{(r,c) \mid \max_{t} h_{t,r,c} \ge 0.05\text{ m}\}$ is the set of all cells that are **ever wet** during the simulation.
- **Distinction from Metric 4 (`wet_iou`)**: `wet_iou` only checks the single final snapshot ($t=120$), missing transient peak flooding that drained before the final step. `peak_extent_iou` captures the true maximum hazard footprint.

---

## 3. Configuration Proposal: `boundary_condition`

We propose adding an optional key to `config.json`:
```json
{
  "boundary_condition": "closed"
}
```
- `"closed"`: No-flux solid walls along the domain boundary ($\mathbf{u} \cdot \mathbf{n} = 0$). All runoff remains in the grid unless removed by drainage sinks (`cum_outflow_m3_series` is identically zero).
- `"open"`: Free outflow / transmissive boundary allowing water to leave the catchment along downhill slopes (e.g., south-east corner).

> **Note**: In accordance with the non-breaking rule, `boundary_condition` is **not set in config.json yet** and remains an open design decision for the ML teammate.

---

## 4. Questions for the ML Teammate

Before finalizing Contract v1.1 into binding specifications, please review and answer the following three questions regarding the SWE solver implementation:

1. **Boundary Conditions**:
   - Should we configure the 2D SWE solver with **closed boundaries** (no water leaves the 2.56 km domain) or **open boundaries** (critical flow / transmissive condition on the boundary)?
   - *Backend recommendation*: Start with `"closed"` boundaries for the hackathon baseline. It simplifies mass budgeting ($\text{outflow} \equiv 0$) and avoids artificial reflection artifacts.

2. **Drainage Sink Mechanics**:
   - In urban hydrology, does `drain_capacity_mmhr` apply **only to wet cells** ($h > 0$), or uniformly across the domain?
   - If a cell is dry ($h = 0$) and rain intensity $R < D$, does the drain instantly swallow the rain ($h$ remains $0$)?
   - *Backend recommendation*: In each cell with precipitation $R_t$ and depth $h_t$, maximum infiltration rate is $D$. Water depth update: $\Delta h = \max(-h_t, (R_t - D) \Delta t)$.

3. **Boundary Outflow Measurement**:
   - If open boundaries are selected, how will the solver report cumulative boundary flux?
   - Can the numerical scheme log the line integral $\Delta V_{\text{outflow}} = \Delta t \oint_{\partial \Omega} h (\mathbf{u} \cdot \mathbf{n}) \, ds$ at each time step?

---

## 5. Summary of Schema Changes (Additive)

```
ForecastResponse:
  + volume_m3_series: Optional[List[float]]
  + cum_rain_m3_series: Optional[List[float]]
  + cum_drain_m3_series: Optional[List[float]]
  + cum_outflow_m3_series: Optional[List[float]]
  + mass_residual_series: Optional[List[float]]

SolverResponse:
  + volume_m3_series: Optional[List[float]]
  + cum_rain_m3_series: Optional[List[float]]
  + cum_drain_m3_series: Optional[List[float]]
  + cum_outflow_m3_series: Optional[List[float]]
  + mass_residual_series: Optional[List[float]]

MetricsResponse:
  + mae_series: Optional[List[float]]
  + mass_residual_series: Optional[List[float]]
  + solver_mass_residual_series: Optional[List[float]]
  + peak_extent_iou: Optional[float]
```
