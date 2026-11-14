"""Loss functions and accuracy evaluation meters for neural surrogate training.

Baseline Loss:
- Weighted Huber loss on normalized depth increment (delta_h)
- 5x weight multiplier on inundated cells (depth >= 0.05 m)
- Small unweighted term on dry cells to prevent phantom flooding

Accuracy Meter:
- Computes MAE (m), RMSE (m), Wet IoU (>= 0.05m), and 5mm physical accuracy percentage.

Phase: Phase 4 (Baseline Surrogate)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class WeightedHuberLoss(nn.Module):
    """Huber loss on depth increments with spatial weighting on wet cells.

    Weights inundated cells (target depth >= 0.05 m) higher (default 5.0x)
    so the model focuses capacity on active flood waves while preserving dry state.
    """

    def __init__(
        self,
        delta: float = 1.0,
        wet_weight: float = 5.0,
        wet_threshold_m: float = 0.05,
    ) -> None:
        super().__init__()
        self.delta = delta
        self.wet_weight = wet_weight
        self.wet_threshold_m = wet_threshold_m

    def forward(
        self,
        pred_delta_norm: torch.Tensor,
        target_delta_norm: torch.Tensor,
        target_next_depth_m: torch.Tensor,
    ) -> torch.Tensor:
        """Compute weighted Huber loss.

        Parameters
        ----------
        pred_delta_norm : torch.Tensor
            Predicted normalized increment (B, C, H, W).
        target_delta_norm : torch.Tensor
            Target normalized increment (B, C, H, W).
        target_next_depth_m : torch.Tensor
            Ground truth water depth at t+1 in meters (B, C, H, W).
        """
        # Elementwise Huber loss
        diff = pred_delta_norm - target_delta_norm
        abs_diff = torch.abs(diff)
        huber = torch.where(
            abs_diff <= self.delta,
            0.5 * (diff ** 2),
            self.delta * (abs_diff - 0.5 * self.delta),
        )

        # Spatial weighting
        wet_mask = (target_next_depth_m >= self.wet_threshold_m).float()
        weights = 1.0 + (self.wet_weight - 1.0) * wet_mask

        return torch.mean(weights * huber)


class AccuracyMeter:
    """Tracks and reports real-time surrogate physical accuracy metrics."""

    def __init__(self, wet_threshold_m: float = 0.05) -> None:
        self.wet_threshold_m = wet_threshold_m
        self.reset()

    def reset(self) -> None:
        self.total_cells = 0
        self.sum_abs_err_m = 0.0
        self.sum_sq_err_m = 0.0
        self.accurate_2mm_cells = 0
        self.accurate_5mm_cells = 0
        self.accurate_10mm_cells = 0
        self.wet_intersection = 0
        self.wet_union = 0
        self.peak_abs_err_m = 0.0
        self.batch_count = 0
        self.total_loss = 0.0

    @torch.no_grad()
    def update(
        self,
        pred_depth_m: torch.Tensor,
        target_depth_m: torch.Tensor,
        loss_val: float = 0.0,
    ) -> None:
        """Update running metrics with a batch of predictions and targets."""
        diff_m = torch.abs(pred_depth_m - target_depth_m)

        batch_cells = diff_m.numel()
        self.total_cells += batch_cells
        self.sum_abs_err_m += float(torch.sum(diff_m).item())
        self.sum_sq_err_m += float(torch.sum(diff_m ** 2).item())
        self.accurate_2mm_cells += int(torch.sum(diff_m <= 0.002).item())
        self.accurate_5mm_cells += int(torch.sum(diff_m <= 0.005).item())
        self.accurate_10mm_cells += int(torch.sum(diff_m <= 0.010).item())
        self.peak_abs_err_m = max(self.peak_abs_err_m, float(torch.max(diff_m).item()))

        pred_wet = pred_depth_m >= self.wet_threshold_m
        true_wet = target_depth_m >= self.wet_threshold_m
        inter = torch.logical_and(pred_wet, true_wet).sum().item()
        union = torch.logical_or(pred_wet, true_wet).sum().item()
        self.wet_intersection += int(inter)
        self.wet_union += int(union)

        self.total_loss += loss_val
        self.batch_count += 1

    def compute(self) -> Dict[str, float]:
        """Compute aggregated metrics dictionary."""
        if self.total_cells == 0:
            return {
                "loss": 0.0,
                "mae_m": 0.0,
                "mae_mm": 0.0,
                "rmse_m": 0.0,
                "rmse_mm": 0.0,
                "wet_iou": 1.0,
                "accuracy_2mm_pct": 100.0,
                "accuracy_5mm_pct": 100.0,
                "accuracy_10mm_pct": 100.0,
                "peak_err_m": 0.0,
            }

        mae = self.sum_abs_err_m / self.total_cells
        rmse = math.sqrt(self.sum_sq_err_m / self.total_cells)
        iou = (
            float(self.wet_intersection) / float(self.wet_union)
            if self.wet_union > 0
            else 1.0
        )
        acc_2mm_pct = (float(self.accurate_2mm_cells) / float(self.total_cells)) * 100.0
        acc_5mm_pct = (float(self.accurate_5mm_cells) / float(self.total_cells)) * 100.0
        acc_10mm_pct = (float(self.accurate_10mm_cells) / float(self.total_cells)) * 100.0
        avg_loss = self.total_loss / max(1, self.batch_count)

        return {
            "loss": avg_loss,
            "mae_m": mae,
            "mae_mm": mae * 1000.0,
            "rmse_m": rmse,
            "rmse_mm": rmse * 1000.0,
            "wet_iou": iou,
            "accuracy_2mm_pct": acc_2mm_pct,
            "accuracy_5mm_pct": acc_5mm_pct,
            "accuracy_10mm_pct": acc_10mm_pct,
            "peak_err_m": self.peak_abs_err_m,
        }

    def format_meter(self, prefix: str = "") -> str:
        """Format an informative accuracy meter string."""
        m = self.compute()
        p = f"{prefix} " if prefix else ""
        return (
            f"{p}Loss: {m['loss']:.5f} | "
            f"MAE: {m['mae_mm']:5.2f}mm | RMSE: {m['rmse_mm']:5.2f}mm | "
            f"Wet IoU: {m['wet_iou']:.4f} | "
            f"Acc(±2mm): {m['accuracy_2mm_pct']:5.1f}% | Acc(±5mm): {m['accuracy_5mm_pct']:5.1f}% | "
            f"Acc(±10mm): {m['accuracy_10mm_pct']:5.1f}% | Peak Err: {m['peak_err_m']:.3f}m"
        )


def nonneg_penalty(pred_depth: torch.Tensor) -> torch.Tensor:
    """Quadratic penalty on unphysical negative depth predictions."""
    return torch.mean(torch.relu(-pred_depth) ** 2)


def mass_conservation_loss(*args: Any, **kwargs: Any) -> torch.Tensor:
    """Physics-informed mass conservation loss placeholder for Phase 5."""
    raise NotImplementedError("Mass conservation loss is scheduled for Phase 5 (--lambda-mass > 0).")


def rollout_loss(*args: Any, **kwargs: Any) -> torch.Tensor:
    """Multi-step unrolled pushforward loss placeholder for Phase 5."""
    raise NotImplementedError("Multi-step rollout training is scheduled for Phase 5 (--pushforward).")
