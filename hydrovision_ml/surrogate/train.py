"""Surrogate model training pipeline.

Supports single-step training, multi-step unrolled training (pushforward trick),
and curriculum learning for autoregressive rollout stability.

Phase: Phase 4 & 5 (Training Pipeline)
Owner: ML Teammate
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional


def train(
    model_name: str = "unet",
    epochs: int = 50,
    device: str = "cpu",
    lambda_mass: float = 0.1,
    pushforward: bool = False,
    data_dir: str = "artifacts/data",
    checkpoint_out: str = "artifacts/models/best.pt",
) -> None:
    """Execute training run for neural surrogate model.

    Parameters
    ----------
    model_name : str
        Architecture choice: "unet" or "conservative".
    epochs : int
        Number of training epochs.
    device : str
        Compute device: "cpu", "cuda", or "mps".
    lambda_mass : float
        Weight multiplier for mass conservation loss.
    pushforward : bool
        Enable multi-step autoregressive rollout during training.
    data_dir : str
        Directory containing train.npz and val.npz.
    checkpoint_out : str
        Output file path for saving best model weights.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 4/5.
    """
    raise NotImplementedError(
        "Planned for Phase 4/5: Neural surrogate training pipeline. "
        f"Will train {model_name} on {device} and write to {checkpoint_out}."
    )


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Train HydroVision neural surrogate model.")
    parser.add_argument(
        "--model",
        type=str,
        default="unet",
        choices=["unet", "conservative"],
        help="Surrogate architecture to train.",
    )
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs.")
    parser.add_argument("--device", type=str, default="cpu", help="Compute device ('cpu', 'cuda', 'mps').")
    parser.add_argument(
        "--lambda-mass",
        type=float,
        default=0.1,
        help="Weight multiplier for mass conservation penalty.",
    )
    parser.add_argument(
        "--pushforward",
        action="store_true",
        default=False,
        help="Enable multi-step unrolled pushforward autoregressive training.",
    )

    parsed = parser.parse_args(args)
    train(
        model_name=parsed.model,
        epochs=parsed.epochs,
        device=parsed.device,
        lambda_mass=parsed.lambda_mass,
        pushforward=parsed.pushforward,
    )


if __name__ == "__main__":
    main(sys.argv[1:])

