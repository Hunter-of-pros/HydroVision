"""Physics-informed loss functions for flood depth surrogate training.

Enforces physical laws including mass conservation, non-negativity of depth,
and multi-step autoregressive rollout stability.

Phase: Phase 5 (Physics-Informed Loss & Stability)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any


def mass_conservation_loss(
    pred_depth: Any,
    prev_depth: Any,
    rain_rate_mmhr: Any,
    drain_capacity_mmhr: Any,
    cell_size_m: float = 40.0,
    dt_s: float = 60.0,
) -> Any:
    """Compute global mass balance discrepancy penalty.

    Total water volume at t+1 must equal water at t + net precipitation input.

    Parameters
    ----------
    pred_depth : torch.Tensor
        Predicted depth at step t+1 of shape (batch, 1, H, W) [m].
    prev_depth : torch.Tensor
        Depth at step t of shape (batch, 1, H, W) [m].
    rain_rate_mmhr : torch.Tensor or float
        Rainfall rate during step [mm/hr].
    drain_capacity_mmhr : torch.Tensor or float
        Drainage infiltration capacity during step [mm/hr].
    cell_size_m : float
        Spatial resolution in meters (40.0m).
    dt_s : float
        Time step interval in seconds (60.0s).

    Returns
    -------
    torch.Tensor
        Scalar penalty: |Total_Pred_Vol - (Total_Prev_Vol + Net_Rain_Vol)|

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 5.
    """
    raise NotImplementedError("Planned for Phase 5: Physics-informed mass conservation loss.")


def nonneg_penalty(pred_depth: Any) -> Any:
    """Penalize unphysical negative water depths.

    Parameters
    ----------
    pred_depth : torch.Tensor
        Predicted depth tensor.

    Returns
    -------
    torch.Tensor
        Mean squared penalty of ReLU(-pred_depth).

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 5.
    """
    raise NotImplementedError("Planned for Phase 5: Non-negativity penalty loss.")


def rollout_loss(
    pred_sequence: Any,
    target_sequence: Any,
    lambda_mass: float = 0.1,
    lambda_nonneg: float = 1.0,
) -> Any:
    """Compute combined multi-step unrolled autoregressive loss over k steps.

    Parameters
    ----------
    pred_sequence : torch.Tensor
        Autoregressively predicted depths over k unrolled steps.
    target_sequence : torch.Tensor
        Ground-truth solver depths over matching steps.
    lambda_mass : float
        Weight for mass conservation penalty.
    lambda_nonneg : float
        Weight for non-negative depth constraint.

    Returns
    -------
    torch.Tensor
        Combined weighted scalar loss for backpropagation.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 5.
    """
    raise NotImplementedError("Planned for Phase 5: Multi-step rollout loss computation.")

