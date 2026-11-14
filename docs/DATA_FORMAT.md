# HydroVision Dataset Format Specification

This document details the file structure, array shapes, dtypes, physical units, indexing conventions, and parameter encodings for datasets stored under `C:\hydrovision_data\data\`.

---

## 1. Directory Structure

The dataset contains three splits (`train`, `val`, `test`) and one out-of-distribution evaluation split (`extrapolation`), plus a root manifest `metadata.json`:

```text
C:\hydrovision_data\data\
├── metadata.json
├── train/
│   ├── depth.npy        (shape: [280, 121, 64, 64], dtype: float32)
│   ├── rain.npy         (shape: [280, 120],         dtype: float32)
│   ├── drain_m3.npy     (shape: [280, 120],         dtype: float32)
│   ├── params.npy       (shape: [280, 4],           dtype: float32)
│   └── params.json
├── val/
│   ├── depth.npy        (shape: [60, 121, 64, 64],  dtype: float32)
│   ├── rain.npy         (shape: [60, 120],          dtype: float32)
│   ├── drain_m3.npy     (shape: [60, 120],          dtype: float32)
│   ├── params.npy       (shape: [60, 4],            dtype: float32)
│   └── params.json
├── test/
│   ├── depth.npy        (shape: [60, 121, 64, 64],  dtype: float32)
│   ├── rain.npy         (shape: [60, 120],          dtype: float32)
│   ├── drain_m3.npy     (shape: [60, 120],          dtype: float32)
│   ├── params.npy       (shape: [60, 4],            dtype: float32)
│   └── params.json
└── extrapolation/
    ├── depth.npy        (shape: [30, 121, 64, 64],  dtype: float32)
    ├── rain.npy         (shape: [30, 120],          dtype: float32)
    ├── drain_m3.npy     (shape: [30, 120],          dtype: float32)
    ├── params.npy       (shape: [30, 4],            dtype: float32)
    └── params.json
```

All `.npy` files are stored in uncompressed standard binary format, enabling zero-copy memory mapping (`np.load(path, mmap_mode='r')`). Total dataset storage is ~814 MB.

---

## 2. Array Definitions & Physical Units

### `depth.npy`
- **Shape**: `(N, 121, 64, 64)`
- **Dtype**: `float32`
- **Units**: Water depth in **meters** ($m$) above ground level.
- **Index Convention**:
  - Dimension 0: Scenario index ($0 \dots N-1$).
  - Dimension 1: Time frame $t \in [0, 120]$. Frame $t=0$ corresponds to $0\text{ min}$ (dry initial state: all zeros). Frames $t \in [1, 120]$ correspond to elapsed times $t \times 60\text{ s} = t\text{ min}$.
  - Dimension 2 & 3: Spatial grid coordinates (row $0 \dots 63$, col $0 \dots 63$). North is row 0, West is col 0. Cell size is $\Delta x = 60.9\text{ m}$.

### `rain.npy`
- **Shape**: `(N, 120)`
- **Dtype**: `float32`
- **Units**: Rainfall rate in **millimeters per hour** ($mm/hr$).
- **Index Convention**: `rain[i, k]` is the uniform rainfall intensity applied over the time interval from $t = k\text{ min}$ to $t = (k + 1)\text{ min}$ (for $k \in [0, 119]$).

### `drain_m3.npy`
- **Shape**: `(N, 120)`
- **Dtype**: `float32`
- **Meaning**: **CUMULATIVE drained/infiltrated volume** (Hypothesis H2 confirmed).
- **Units**: **Cubic meters** ($m^3$) aggregated over the entire $64 \times 64$ domain.
- **Index Convention**:
  - `drain_m3[i, k]` (where $k \in [0, 119]$) is the total volume of water drained from time $t = 0$ up to macro output step $t = k + 1$ (frame $k + 1$ in `depth.npy`).
  - At $t=0$ (frame 0), cumulative drainage is identically $0.0\text{ m}^3$.
- **Mass Balance Equation**:
  For any time frame $t \in [1, 120]$:
  $$\text{stored}[t] = \text{cum\_rain}[t] - \text{drain\_m3}[t-1]$$
  where:
  - $\text{stored}[t] = \sum_{r,c} \text{depth}[t, r, c] \times (60.9)^2 \quad [m^3]$
  - $\text{cum\_rain}[t] = \sum_{j=0}^{t-1} \left(\frac{\text{rain}[j]}{1000 \times 3600} \times 60.0\right) \times (64 \times 64 \times 60.9^2) \quad [m^3]$

### `params.npy`
- **Shape**: `(N, 4)`
- **Dtype**: `float32`
- **Columns**:
  - `Column 0`: `rain_intensity_mmhr` (float, range $[20.0, 150.0]$ for train/val/test; $[150.0, 180.0]$ for extrapolation).
  - `Column 1`: `rain_duration_min` (float, range $[15.0, 90.0]$).
  - `Column 2`: `rain_shape` (integer code as float):
    - `0` = `"constant"`
    - `1` = `"triangular"`
    - `2` = `"double_peak"`
  - `Column 3`: `drain_capacity_mmhr` (float, range $[0.0, 30.0]$).
