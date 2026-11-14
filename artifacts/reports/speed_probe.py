"""Phase 0 Step 6: Speed Feasibility Probe only.
Appends speed_probe key to solver_benchmark.json.
Run from project root: python artifacts/reports/speed_probe.py
"""
from __future__ import annotations
import json, os, sys, time
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import torch
import torch.nn as nn

print(f"Torch: {torch.__version__}  CUDA: {torch.cuda.is_available()}")

class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.ReLU(inplace=True),
        )
    def forward(self, x): return self.net(x)

class TinyUNet(nn.Module):
    def __init__(self, in_ch=7, out_ch=1, width=32):
        super().__init__()
        self.enc1 = DoubleConv(in_ch, width)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = DoubleConv(width, width * 2)
        self.pool2 = nn.MaxPool2d(2)
        self.bottleneck = DoubleConv(width * 2, width * 4)
        self.up2 = nn.ConvTranspose2d(width * 4, width * 2, 2, stride=2)
        self.dec2 = DoubleConv(width * 4, width * 2)
        self.up1 = nn.ConvTranspose2d(width * 2, width, 2, stride=2)
        self.dec1 = DoubleConv(width * 2, width)
        self.out = nn.Conv2d(width, out_ch, 1)
    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        b  = self.bottleneck(self.pool2(e2))
        d2 = self.dec2(torch.cat([self.up2(b), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return torch.relu(self.out(d1))

model = TinyUNet(in_ch=7, out_ch=1, width=32)
model.eval()
model_bundled = TinyUNet(in_ch=7, out_ch=5, width=32)
model_bundled.eval()

params = sum(p.numel() for p in model.parameters())
print(f"U-Net parameters: {params:,}")

STEPS = 120
N_B1   = 10   # batch=1 runs
N_B64  = 3    # batch=64 runs (slow on CPU)
N_BUND = 10   # bundled runs

static_1  = torch.randn(1,  7, 64, 64)
static_64 = torch.randn(64, 7, 64, 64)

# ---- Batch=1 autoregressive ----
print(f"Batch=1, {STEPS} steps, {N_B1} runs...")
t_b1 = []
for i in range(N_B1):
    x = static_1.clone()
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(STEPS):
            pred = model(x)
            x = torch.cat([pred, x[:, 1:]], dim=1)
    t_b1.append(time.perf_counter() - t0)
    print(f"  run {i+1}/{N_B1}: {t_b1[-1]*1000:.1f}ms", flush=True)
med_b1 = float(np.median(t_b1))
print(f"  -> median {med_b1*1000:.1f}ms")

# ---- Batch=64 autoregressive ----
print(f"Batch=64, {STEPS} steps, {N_B64} runs...")
t_b64 = []
for i in range(N_B64):
    x = static_64.clone()
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(STEPS):
            pred = model(x)
            x = torch.cat([pred, x[:, 1:]], dim=1)
    t_b64.append(time.perf_counter() - t0)
    print(f"  run {i+1}/{N_B64}: {t_b64[-1]*1000:.0f}ms  ({t_b64[-1]*1000/64:.1f}ms/scenario)", flush=True)
med_b64 = float(np.median(t_b64))
print(f"  -> median {med_b64*1000:.1f}ms total, {med_b64*1000/64:.1f}ms/scenario")

# ---- Bundled variant (5-step/pass, 24 passes, batch=1) ----
PASSES = STEPS // 5
print(f"Bundled: {PASSES} passes × 5 steps, batch=1, {N_BUND} runs...")
t_bund = []
for i in range(N_BUND):
    x = static_1.clone()
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(PASSES):
            pred5 = model_bundled(x)
            last = pred5[:, -1:]
            x = torch.cat([last, x[:, 1:]], dim=1)
    t_bund.append(time.perf_counter() - t0)
    print(f"  run {i+1}/{N_BUND}: {t_bund[-1]*1000:.1f}ms", flush=True)
med_bund = float(np.median(t_bund))
print(f"  -> median {med_bund*1000:.1f}ms")

# ---- Load existing benchmark and append ----
bench_path = os.path.join(ROOT, "artifacts", "reports", "solver_benchmark.json")
with open(bench_path) as f:
    bench = json.load(f)
solver_ms = bench["median_ms"]

speedup_b1   = solver_ms / (med_b1 * 1000)
speedup_per_b64 = solver_ms / (med_b64 * 1000 / 64)
speedup_bund = solver_ms / (med_bund * 1000)

probe = {
    "torch_version": torch.__version__,
    "device": "cpu",
    "unet_params": params,
    "n_runs_b1": N_B1, "n_runs_b64": N_B64, "n_runs_bundled": N_BUND,
    "solver_median_ms": solver_ms,
    "unet_batch1_120step_median_ms": round(med_b1 * 1000, 2),
    "unet_batch64_120step_median_ms": round(med_b64 * 1000, 2),
    "unet_batch64_per_scenario_ms": round(med_b64 * 1000 / 64, 2),
    "unet_bundled_24pass_median_ms": round(med_bund * 1000, 2),
    "speedup_batch1": round(speedup_b1, 3),
    "speedup_batch64_per_scenario": round(speedup_per_b64, 3),
    "speedup_bundled_batch1": round(speedup_bund, 3),
}
bench["speed_probe"] = probe
with open(bench_path, "w") as f:
    json.dump(bench, f, indent=2)
print(f"\nSaved speed_probe -> {bench_path}")

print(f"""
┌──────────────────────────────────────────────────────────────────────┐
│       SPEED FEASIBILITY PROBE — CPU (untrained U-Net, {params:,} params) │
├──────────────────────────────────┬────────────┬──────────────────────┤
│  Mode                            │ Median(ms) │ Speedup vs Solver    │
├──────────────────────────────────┼────────────┼──────────────────────┤
│  Solver (1 scenario, 120 steps)  │ {solver_ms:>10.1f} │ 1.00×  (reference)   │
│  U-Net batch=1  (120 AR passes)  │ {med_b1*1000:>10.1f} │ {speedup_b1:>5.2f}×                │
│  U-Net batch=64 per scenario*    │ {med_b64*1000/64:>10.1f} │ {speedup_per_b64:>5.2f}×  (ensemble)   │
│  U-Net bundled  (24 passes×5)    │ {med_bund*1000:>10.1f} │ {speedup_bund:>5.2f}×                │
└──────────────────────────────────┴────────────┴──────────────────────┘
  * batch=64 total={med_b64*1000:.0f}ms ÷ 64 = {med_b64*1000/64:.1f}ms/scenario (ensemble throughput)
  NOTE: All timings are CPU-only (torch {torch.__version__}). No CUDA wheel available for Python 3.15 yet.
""")
