import json
import os
from pathlib import Path
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )
    def forward(self, x):
        return self.net(x)

class BundledUNet(nn.Module):
    def __init__(self, in_ch=12, out_ch=5, base_ch=25):
        super().__init__()
        self.inc = DoubleConv(in_ch, base_ch)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(base_ch, base_ch * 2))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(base_ch * 2, base_ch * 4))
        self.up1 = nn.ConvTranspose2d(base_ch * 4, base_ch * 2, 2, stride=2)
        self.conv_up1 = DoubleConv(base_ch * 4, base_ch * 2)
        self.up2 = nn.ConvTranspose2d(base_ch * 2, base_ch, 2, stride=2)
        self.conv_up2 = DoubleConv(base_ch * 2, base_ch)
        self.outc = nn.Conv2d(base_ch, out_ch, 1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        u1 = self.up1(x3)
        u1 = torch.cat([u1, x2], dim=1)
        u1 = self.conv_up1(u1)
        u2 = self.up2(u1)
        u2 = torch.cat([u2, x1], dim=1)
        u2 = self.conv_up2(u2)
        return self.outc(u2)

def time_forward(model, batch_size, num_runs=7, warmup=3):
    x = torch.randn(batch_size, 12, 64, 64)
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(x)
        times = []
        for _ in range(num_runs):
            t0 = time.perf_counter()
            _ = model(x)
            times.append(time.perf_counter() - t0)
    return float(np.median(times))

def time_train_step(model, optimizer, criterion, batch_size, num_runs=5, warmup=2):
    x = torch.randn(batch_size, 12, 64, 64)
    y = torch.randn(batch_size, 5, 64, 64)
    for _ in range(warmup):
        optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
    times = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        times.append(time.perf_counter() - t0)
    return float(np.median(times))

def main():
    torch.set_num_threads(8)
    model = BundledUNet(in_ch=12, out_ch=5, base_ch=25)
    model.eval()
    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[Speed Probe] Bundled U-Net (in=12, out=5): {param_count:,} parameters (~288k)")

    # 1. Forward pass timings at 8 threads for batch 1, 8, 32
    print("[Speed Probe] Measuring forward pass latency at 8 threads...")
    fwd_1_s = time_forward(model, 1, num_runs=7, warmup=3)
    fwd_8_s = time_forward(model, 8, num_runs=7, warmup=3)
    fwd_32_s = time_forward(model, 32, num_runs=7, warmup=3)
    print(f"  Forward B=1:  {fwd_1_s*1000:.2f} ms")
    print(f"  Forward B=8:  {fwd_8_s*1000:.2f} ms ({fwd_8_s*1000/8:.2f} ms/sample)")
    print(f"  Forward B=32: {fwd_32_s*1000:.2f} ms ({fwd_32_s*1000/32:.2f} ms/sample)")

    # 2. Training step timings at batch 16 and 32
    print("[Speed Probe] Measuring training step time (forward + backward + AdamW)...")
    model.train()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.HuberLoss()
    train_16_s = time_train_step(model, optimizer, criterion, 16, num_runs=5, warmup=2)
    train_32_s = time_train_step(model, optimizer, criterion, 32, num_runs=5, warmup=2)
    print(f"  Train Step B=16: {train_16_s*1000:.2f} ms")
    print(f"  Train Step B=32: {train_32_s*1000:.2f} ms")

    # 3. Thread comparison for batch-8 forward
    model.eval()
    print("[Speed Probe] Comparing thread counts {4, 8, 12} for batch-8 forward...")
    thread_timings = {}
    for th in [4, 8, 12]:
        torch.set_num_threads(th)
        t_th = time_forward(model, 8, num_runs=5, warmup=2)
        thread_timings[th] = t_th
        print(f"  Threads={th:2d}: {t_th*1000:.2f} ms")
    best_threads = min(thread_timings.keys(), key=lambda t: thread_timings[t])
    print(f"  Selected best thread count: {best_threads}")
    torch.set_num_threads(best_threads)

    # 4. Rollout calculations and confirmation runs
    # Solver baseline
    solver_median_s = 0.267

    calc_rollout_bundled_1_s = 24 * fwd_1_s
    calc_rollout_unbundled_1_s = 120 * fwd_1_s
    calc_rollout_per_sc_32_s = (24 * fwd_32_s) / 32.0

    print("\n[Speed Probe] Running confirmation 120-step rollouts (24 bundled forward passes)...")
    # Single confirmation rollout B=1
    x1 = torch.randn(1, 12, 64, 64)
    t0 = time.perf_counter()
    with torch.no_grad():
        for p in range(24):
            _ = model(x1)
    real_rollout_1_s = time.perf_counter() - t0

    # Single confirmation rollout B=8
    x8 = torch.randn(8, 12, 64, 64)
    t0 = time.perf_counter()
    with torch.no_grad():
        for p in range(24):
            _ = model(x8)
    real_rollout_8_total_s = time.perf_counter() - t0
    real_rollout_8_per_sc_s = real_rollout_8_total_s / 8.0

    diff_1 = abs(real_rollout_1_s - calc_rollout_bundled_1_s) / calc_rollout_bundled_1_s
    diff_8 = abs(real_rollout_8_per_sc_s - (24 * fwd_8_s / 8.0)) / (24 * fwd_8_s / 8.0)

    print(f"  B=1 Rollout: Calc={calc_rollout_bundled_1_s*1000:.1f} ms, Real={real_rollout_1_s*1000:.1f} ms (diff: {diff_1*100:.1f}%)")
    print(f"  B=8 Rollout: Calc={24*fwd_8_s/8*1000:.1f} ms, Real={real_rollout_8_per_sc_s*1000:.1f} ms (diff: {diff_8*100:.1f}%)")

    # Speedups
    single_speedup = solver_median_s / real_rollout_1_s
    batched_speedup_8 = solver_median_s / real_rollout_8_per_sc_s
    batched_speedup_32 = solver_median_s / calc_rollout_per_sc_32_s

    # 5. Training Epoch Estimates (Sliding windows over 280 scenarios, windows t=0..115 -> 116 windows/scenario = 32,480 samples)
    total_samples = 280 * 116  # 32,480
    steps_full = total_samples // 32  # 1,015 steps
    epoch_full_s = steps_full * train_32_s
    total_30_full_min = (30 * epoch_full_s) / 60.0

    steps_25 = int(steps_full * 0.25)  # 253 steps
    epoch_25_s = steps_25 * train_32_s
    total_30_25_min = (30 * epoch_25_s) / 60.0

    print("\n" + "=" * 70)
    print("SPEED PROBE & SOLVER COMPARISON TABLE (CPU, Bundled k=5):")
    print("-" * 70)
    print(f"Reference Solver (Median):          {solver_median_s*1000:>8.1f} ms (1.00x)")
    print(f"Surrogate Single B=1 (Bundled k=5): {real_rollout_1_s*1000:>8.1f} ms ({single_speedup:.2f}x speedup)")
    print(f"Surrogate Batched B=8 (per-sc):     {real_rollout_8_per_sc_s*1000:>8.1f} ms ({batched_speedup_8:.2f}x speedup)")
    print(f"Surrogate Batched B=32 (per-sc):    {calc_rollout_per_sc_32_s*1000:>8.1f} ms ({batched_speedup_32:.2f}x speedup)")
    print("=" * 70)

    probe_data = {
        "model": "BundledUNet",
        "parameters": param_count,
        "input_channels": 12,
        "output_channels": 5,
        "bundling_k": 5,
        "hardware": "Intel Core i9-12900H (CPU)",
        "selected_threads": best_threads,
        "thread_comparison_forward_b8_ms": {str(k): round(v*1000, 2) for k, v in thread_timings.items()},
        "forward_latency_ms": {
            "batch_1": round(fwd_1_s * 1000, 2),
            "batch_8": round(fwd_8_s * 1000, 2),
            "batch_32": round(fwd_32_s * 1000, 2),
        },
        "train_step_latency_ms": {
            "batch_16": round(train_16_s * 1000, 2),
            "batch_32": round(train_32_s * 1000, 2),
        },
        "rollout_120_step": {
            "solver_baseline_s": solver_median_s,
            "single_b1_calculated_s": round(calc_rollout_bundled_1_s, 4),
            "single_b1_measured_s": round(real_rollout_1_s, 4),
            "single_b1_speedup": round(single_speedup, 2),
            "unbundled_120_passes_calculated_s": round(calc_rollout_unbundled_1_s, 4),
            "batched_b8_measured_per_sc_s": round(real_rollout_8_per_sc_s, 4),
            "batched_b8_speedup": round(batched_speedup_8, 2),
            "batched_b32_calculated_per_sc_s": round(calc_rollout_per_sc_32_s, 4),
            "batched_b32_speedup": round(batched_speedup_32, 2),
        },
        "training_epoch_estimates": {
            "full_sliding_windows": {
                "samples": total_samples,
                "batch_size": 32,
                "steps": steps_full,
                "one_epoch_time_s": round(epoch_full_s, 1),
                "one_epoch_time_min": round(epoch_full_s / 60.0, 2),
                "total_30_epochs_min": round(total_30_full_min, 1),
                "total_30_epochs_hours": round(total_30_full_min / 60.0, 2),
            },
            "subsampled_25pct_windows": {
                "samples": int(total_samples * 0.25),
                "batch_size": 32,
                "steps": steps_25,
                "one_epoch_time_s": round(epoch_25_s, 1),
                "one_epoch_time_min": round(epoch_25_s / 60.0, 2),
                "total_30_epochs_min": round(total_30_25_min, 1),
            },
        },
    }

    out_file = Path("artifacts/reports/speed_probe.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(probe_data, f, indent=2)
    print(f"\n[Speed Probe] Saved full report to: {out_file}")

if __name__ == "__main__":
    main()
