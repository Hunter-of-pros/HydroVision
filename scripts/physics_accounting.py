import json
import os
from pathlib import Path
import numpy as np

data_dir = r"C:\hydrovision_data\data\train"

depth_mmap = np.load(os.path.join(data_dir, "depth.npy"), mmap_mode="r")  # (280, 121, 64, 64) float32
rain_arr = np.load(os.path.join(data_dir, "rain.npy"))                    # (280, 120) float32
drain_arr = np.load(os.path.join(data_dir, "drain_m3.npy"))               # (280, 120) float32
params_arr = np.load(os.path.join(data_dir, "params.npy"))               # (280, 4) float32

dx = 60.9
cell_area = dx ** 2
domain_cells = 64 * 64
domain_area = domain_cells * cell_area

num_sc = 30

# 1. Budget verifications: per-step and 5-step window
per_step_rel_residuals = []
window_5_rel_residuals = []

# 2. Formula drainage error
formula_per_step_errors_rel_drain = []
formula_per_step_errors_rel_tot_rain = []
formula_window5_errors_rel_tot_rain = []

for sc_idx in range(num_sc):
    d = depth_mmap[sc_idx]  # (121, 64, 64)
    r = rain_arr[sc_idx]    # (120,)
    # cum_drain at frame 0 is 0; frame k is drain_arr[sc_idx, k-1] for k in 1..120
    cum_dr = np.zeros(121, dtype=np.float64)
    cum_dr[1:] = drain_arr[sc_idx].astype(np.float64)

    # Volume at each frame t in 0..120
    v = np.sum(d.astype(np.float64), axis=(1, 2)) * cell_area  # (121,)

    # Rain volume per step t in 0..119
    rain_vol_step = (r.astype(np.float64) / 1000.0 / 3600.0 * 60.0) * domain_area  # (120,)
    total_rain_vol = float(np.sum(rain_vol_step))

    # Drain capacity in m/s
    cap_mmhr = float(params_arr[sc_idx, 3])
    cap_mps = cap_mmhr / 1000.0 / 3600.0
    cap_step_m = cap_mps * 60.0

    # (a) Per-step budget: V[t+1] - V[t] = rain_vol[t] - (cum_dr[t+1] - cum_dr[t])
    delta_v = v[1:] - v[:-1]  # (120,)
    true_step_drain = cum_dr[1:] - cum_dr[:-1]  # (120,)
    per_step_res = np.abs(delta_v - (rain_vol_step - true_step_drain))
    per_step_rel_residuals.extend(per_step_res / max(total_rain_vol, 1.0))

    # (b) 5-step window budget: V[t+5] - V[t] = sum(rain[t..t+4]) - (cum_dr[t+5] - cum_dr[t])
    for t in range(0, 120 - 4):
        delta_v_5 = v[t + 5] - v[t]
        rain_5 = np.sum(rain_vol_step[t : t + 5])
        drain_5 = cum_dr[t + 5] - cum_dr[t]
        res_5 = abs(delta_v_5 - (rain_5 - drain_5))
        window_5_rel_residuals.append(res_5 / max(total_rain_vol, 1.0))

    # (c) Formula estimate of per-step drainage
    for t in range(120):
        h_t = d[t].astype(np.float64)
        rain_depth = (r[t] / 1000.0 / 3600.0) * 60.0
        # Formula: sum over cells of min(h_t + rain_depth_step, cap_m_per_s * 60) * cell_area
        drain_est_t = float(np.sum(np.minimum(h_t + rain_depth, cap_step_m)) * cell_area)
        true_drain_t = float(true_step_drain[t])

        err = abs(drain_est_t - true_drain_t)
        if true_drain_t > 1.0:
            formula_per_step_errors_rel_drain.append(err / true_drain_t)
        formula_per_step_errors_rel_tot_rain.append(err / max(total_rain_vol, 1.0))

    # (d) Window-level version: sum of the 5 per-step estimates using true intermediate depths
    for t in range(0, 120 - 4):
        drain_est_5 = 0.0
        for dt_idx in range(5):
            curr_t = t + dt_idx
            h_curr = d[curr_t].astype(np.float64)
            r_curr = (r[curr_t] / 1000.0 / 3600.0) * 60.0
            drain_est_5 += float(np.sum(np.minimum(h_curr + r_curr, cap_step_m)) * cell_area)
        true_drain_5 = float(cum_dr[t + 5] - cum_dr[t])
        err_5 = abs(drain_est_5 - true_drain_5)
        formula_window5_errors_rel_tot_rain.append(err_5 / max(total_rain_vol, 1.0))

max_step_res = float(np.max(per_step_rel_residuals))
mean_step_res = float(np.mean(per_step_rel_residuals))
max_win5_res = float(np.max(window_5_rel_residuals))
mean_win5_res = float(np.mean(window_5_rel_residuals))

f_mean_err_rel_drain = float(np.mean(formula_per_step_errors_rel_drain)) if formula_per_step_errors_rel_drain else 0.0
f_max_err_rel_drain = float(np.max(formula_per_step_errors_rel_drain)) if formula_per_step_errors_rel_drain else 0.0
f_mean_err_rel_tot_rain = float(np.mean(formula_per_step_errors_rel_tot_rain))
f_max_err_rel_tot_rain = float(np.max(formula_per_step_errors_rel_tot_rain))
f_win5_max_err_rel_tot_rain = float(np.max(formula_window5_errors_rel_tot_rain))
f_win5_mean_err_rel_tot_rain = float(np.mean(formula_window5_errors_rel_tot_rain))

# Recommendation: (a) true drain or (b) formula
# Rule: recommend (b) only if residual is below 2% of total rain volume
rec_choice = "formula" if f_win5_max_err_rel_tot_rain < 0.02 else "true_window_drain"

print("=== PHYSICS ACCOUNTING SUMMARY (30 TRAIN SCENARIOS) ===")
print(f"Per-step Budget Residual:   Mean={mean_step_res:.6e}, Max={max_step_res:.6e}")
print(f"5-step Window Residual:     Mean={mean_win5_res:.6e}, Max={max_win5_res:.6e}")
print(f"Formula Error (rel drain):  Mean={f_mean_err_rel_drain*100:.2f}%, Max={f_max_err_rel_drain*100:.2f}%")
print(f"Formula Error (rel rain):   Mean={f_mean_err_rel_tot_rain*100:.4f}%, Max={f_max_err_rel_tot_rain*100:.4f}%")
print(f"Formula Win5 Error (rel rain): Mean={f_win5_mean_err_rel_tot_rain*100:.4f}%, Max={f_win5_max_err_rel_tot_rain*100:.4f}%")
print(f"Recommendation: {rec_choice}")

results_dict = {
    "scenarios_analyzed": num_sc,
    "budget_verification": {
        "per_step_residual_rel_rain": {
            "mean": mean_step_res,
            "max": max_step_res,
            "status": "PASS" if max_step_res < 1e-4 else "FAIL"
        },
        "window5_residual_rel_rain": {
            "mean": mean_win5_res,
            "max": max_win5_res,
            "status": "PASS" if max_win5_res < 1e-4 else "FAIL"
        }
    },
    "formula_drainage_evaluation": {
        "per_step_error_rel_drain": {
            "mean": f_mean_err_rel_drain,
            "max": f_max_err_rel_drain
        },
        "per_step_error_rel_total_rain": {
            "mean": f_mean_err_rel_tot_rain,
            "max": f_max_err_rel_tot_rain
        },
        "window5_error_rel_total_rain": {
            "mean": f_win5_mean_err_rel_tot_rain,
            "max": f_win5_max_err_rel_tot_rain,
            "under_2_percent": bool(f_win5_max_err_rel_tot_rain < 0.02)
        }
    },
    "recommended_mass_loss_version": rec_choice,
    "recommendation_rationale": (
        "Use true window drain from cum_drain as known training sink: exact conservation with zero formula residual."
        if rec_choice == "true_window_drain" else
        "Formula estimate is accurate within 2% of total scenario rain volume."
    )
}

out_p = Path("artifacts/reports/mass_accounting_check.json")
out_p.parent.mkdir(parents=True, exist_ok=True)
with open(out_p, "w", encoding="utf-8") as f:
    json.dump(results_dict, f, indent=2)
print(f"Saved report to: {out_p}")
