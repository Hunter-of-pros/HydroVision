"""Unit tests for baseline neural surrogate model, normalizer, losses, and rollout.

Tests:
1. Normalizer save/load JSON round-trip equality
2. Model forward pass output shape (B, 1, 64, 64) and parameter count
3. Loss function and AccuracyMeter computation correctness
4. Single-scenario rollout output shape (121, 64, 64) and non-negative depth guarantee
5. Batched rollout output shape (B, 121, 64, 64)
6. Rollout determinism under fixed seed

Phase: Phase 4 (Baseline Surrogate)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import numpy as np
import pytest
import torch

from hydrovision_ml.surrogate.losses import AccuracyMeter, WeightedHuberLoss, nonneg_penalty
from hydrovision_ml.surrogate.model import Normalizer, UNetSurrogate
from hydrovision_ml.surrogate.rollout import rollout, rollout_batched


@pytest.fixture
def dummy_terrain() -> np.ndarray:
    """Create a 64x64 synthetic elevation grid for unit testing."""
    y, x = np.mgrid[0:64, 0:64]
    return (850.0 + 0.1 * x - 0.05 * y).astype(np.float32)


@pytest.fixture
def sample_normalizer() -> Normalizer:
    return Normalizer(
        depth_scale_m=1.5,
        rain_scale_mmhr=150.0,
        drain_scale_mmhr=30.0,
        dem_mean=878.4,
        dem_std=7.55,
        slope_x_mean=-0.0013,
        slope_x_std=0.0175,
        slope_y_mean=-0.0006,
        slope_y_std=0.0183,
        target_delta_std=0.00372,
    )


def test_normalizer_round_trip(sample_normalizer: Normalizer) -> None:
    """Verify Normalizer serializes and deserializes to JSON with identical values."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        sample_normalizer.save(tmp_path)
        loaded = Normalizer.load(tmp_path)

        assert math_close(loaded.depth_scale_m, sample_normalizer.depth_scale_m)
        assert math_close(loaded.rain_scale_mmhr, sample_normalizer.rain_scale_mmhr)
        assert math_close(loaded.drain_scale_mmhr, sample_normalizer.drain_scale_mmhr)
        assert math_close(loaded.dem_mean, sample_normalizer.dem_mean)
        assert math_close(loaded.dem_std, sample_normalizer.dem_std)
        assert math_close(loaded.target_delta_std, sample_normalizer.target_delta_std)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def math_close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) < tol


def test_unet_surrogate_shapes() -> None:
    """Verify UNetSurrogate takes (B, 7, 64, 64) and produces (B, 1, 64, 64)."""
    model = UNetSurrogate(in_channels=7, out_channels=1, base_ch=26, padding_mode="reflect")
    batch_size = 4
    x = torch.randn(batch_size, 7, 64, 64)
    out = model(x)

    assert out.shape == (batch_size, 1, 64, 64)
    assert not torch.isnan(out).any()
    assert not torch.isinf(out).any()

    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert 250_000 < param_count < 350_000, f"Expected ~310k params, got {param_count}"


def test_losses_and_accuracy_meter() -> None:
    """Verify WeightedHuberLoss and AccuracyMeter calculations."""
    criterion = WeightedHuberLoss(wet_weight=5.0, wet_threshold_m=0.05)
    pred_delta = torch.zeros(2, 1, 64, 64)
    target_delta = torch.ones(2, 1, 64, 64) * 0.1
    target_next_depth = torch.zeros(2, 1, 64, 64)

    # All dry cells
    dry_loss = criterion(pred_delta, target_delta, target_next_depth)

    # Inundated cells
    wet_next_depth = torch.ones(2, 1, 64, 64) * 0.2
    wet_loss = criterion(pred_delta, target_delta, wet_next_depth)

    assert wet_loss.item() > dry_loss.item()
    assert math_close(wet_loss.item() / dry_loss.item(), 5.0, tol=1e-3)

    # Nonneg penalty
    neg_depth = torch.tensor([-0.5, 0.5])
    penalty = nonneg_penalty(neg_depth)
    assert penalty.item() > 0.0

    # AccuracyMeter
    meter = AccuracyMeter(wet_threshold_m=0.05)
    pred_m = torch.tensor([[[[0.002, 0.040], [0.060, 0.080]]]])
    true_m = torch.tensor([[[[0.001, 0.041], [0.061, 0.075]]]])
    meter.update(pred_m, true_m, loss_val=0.05)
    metrics = meter.compute()

    assert metrics["accuracy_5mm_pct"] == 100.0
    assert metrics["wet_iou"] == 1.0
    assert metrics["mae_m"] < 0.005


def test_rollout_single_scenario(dummy_terrain: np.ndarray, sample_normalizer: Normalizer) -> None:
    """Verify single-scenario 120-step rollout output shapes and non-negativity."""
    torch.manual_seed(42)
    model = UNetSurrogate(in_channels=7, out_channels=1, base_ch=26)
    model.eval()

    horizon = 12
    rain_series = np.full(horizon, 50.0, dtype=np.float32)

    res = rollout(
        model=model,
        terrain=dummy_terrain,
        rain_series=rain_series,
        drain_capacity_mmhr=10.0,
        normalizer=sample_normalizer,
        cell_size_m=60.9,
        horizon_steps=horizon,
        device="cpu",
    )

    depth_frames = res["depth_frames"]
    assert depth_frames.shape == (horizon + 1, 64, 64)
    assert depth_frames.dtype == np.float32

    # Initial frame 0 must be non-negative
    assert np.all(depth_frames[0] >= 0.0)

    # All frames must respect physical non-negativity
    assert np.all(depth_frames >= 0.0), "Encountered negative depth in rollout!"
    assert res["inference_time_s"] > 0.0


def test_rollout_batched(dummy_terrain: np.ndarray, sample_normalizer: Normalizer) -> None:
    """Verify batched rollout shapes and non-negativity."""
    torch.manual_seed(42)
    model = UNetSurrogate(in_channels=7, out_channels=1, base_ch=26)
    model.eval()

    batch_size = 3
    horizon = 10
    rain_batch = np.full((batch_size, horizon), 40.0, dtype=np.float32)
    drain_batch = np.array([0.0, 10.0, 25.0], dtype=np.float32)

    res = rollout_batched(
        model=model,
        terrain=dummy_terrain,
        rain_batch=rain_batch,
        drain_capacities=drain_batch,
        normalizer=sample_normalizer,
        cell_size_m=60.9,
        horizon_steps=horizon,
        device="cpu",
    )

    depth_frames = res["depth_frames"]
    assert depth_frames.shape == (batch_size, horizon + 1, 64, 64)
    assert np.all(depth_frames >= 0.0)


def test_rollout_determinism(dummy_terrain: np.ndarray, sample_normalizer: Normalizer) -> None:
    """Verify fixed-weight rollout produces bitwise identical predictions across runs."""
    torch.manual_seed(123)
    model = UNetSurrogate(in_channels=7, out_channels=1, base_ch=26)
    model.eval()

    horizon = 8
    rain_series = np.linspace(20.0, 80.0, horizon, dtype=np.float32)

    res1 = rollout(
        model=model,
        terrain=dummy_terrain,
        rain_series=rain_series,
        drain_capacity_mmhr=5.0,
        normalizer=sample_normalizer,
        cell_size_m=60.9,
        horizon_steps=horizon,
        device="cpu",
    )
    res2 = rollout(
        model=model,
        terrain=dummy_terrain,
        rain_series=rain_series,
        drain_capacity_mmhr=5.0,
        normalizer=sample_normalizer,
        cell_size_m=60.9,
        horizon_steps=horizon,
        device="cpu",
    )

    np.testing.assert_array_equal(res1["depth_frames"], res2["depth_frames"])
