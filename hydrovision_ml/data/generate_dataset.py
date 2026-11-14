"""Batch hydrodynamic simulation script for generating surrogate training datasets.

Phase: Phase 3 (Dataset Generation)
Owner: ML Teammate
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional


def generate_dataset(n: int = 100, seed: int = 42, out_dir: str = "artifacts/data") -> None:
    """Run batch hydrodynamic simulations over sampled scenarios and write train/val/test splits.

    Parameters
    ----------
    n : int
        Number of simulation trajectories to produce (default: 100).
    seed : int
        Random seed for sampling scenarios.
    out_dir : str
        Directory where train.npz, val.npz, and test.npz will be saved.

    Raises
    ------
    NotImplementedError
        Scheduled for Phase 3.
    """
    raise NotImplementedError(
        "Planned for Phase 3: Synthetic solver dataset generation. "
        "Use artifacts/data/.gitkeep as destination once implemented."
    )


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate hydrodynamic simulation datasets for surrogate training."
    )
    parser.add_argument("--n", type=int, default=100, help="Number of scenarios to simulate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--out", type=str, default="artifacts/data", help="Output directory path.")

    parsed = parser.parse_args(args)
    generate_dataset(n=parsed.n, seed=parsed.seed, out_dir=parsed.out)


if __name__ == "__main__":
    main(sys.argv[1:])

