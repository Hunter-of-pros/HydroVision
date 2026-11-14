"""Neural network surrogate architectures for rapid flood depth rollout.

Architectures:
- UNetSurrogate: 2D U-Net taking (depth_t, dem, slope_x, slope_y, rain_rate) -> delta_depth
- ConservativeSurrogate: Flux-conserving surrogate predicting edge fluxes (u, v) instead of raw depth
- Normalizer: Standardizes multi-modal spatial inputs and rainfall scalars

Phase: Phase 4 (Baseline Surrogate) & Phase 5 (Physics-Informed Surrogate)
Owner: ML Teammate
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class Normalizer:
    """Mean-variance normalization handler for terrain elevation, rainfall, and depth fields."""

    def __init__(self) -> None:
        self.stats: Dict[str, Dict[str, float]] = {}

    def fit(self, data: Any) -> None:
        """Compute mean and standard deviation from training dataset."""
        raise NotImplementedError("Planned for Phase 4: Normalizer fitting on training split.")

    def transform(self, tensor: Any, key: str) -> Any:
        """Apply z-score normalization to tensor."""
        raise NotImplementedError("Planned for Phase 4: Normalizer transformation.")

    def inverse_transform(self, tensor: Any, key: str) -> Any:
        """Revert z-score normalization back to original physical units."""
        raise NotImplementedError("Planned for Phase 4: Normalizer inverse transformation.")

    def save(self, path: str = "artifacts/models/normalizer.json") -> None:
        """Serialize normalization parameters to disk."""
        raise NotImplementedError("Planned for Phase 4: Save normalizer parameters.")

    def load(self, path: str = "artifacts/models/normalizer.json") -> None:
        """Deserialize normalization parameters from disk."""
        raise NotImplementedError("Planned for Phase 4: Load normalizer parameters.")


class UNetSurrogate:
    """2D U-Net neural surrogate predicting water depth increments (delta depth).

    Input channels (5):
    - Channel 0: Water depth at step t (h_t) [m]
    - Channel 1: Static digital elevation model (DEM) [m]
    - Channel 2: Spatial gradient dz/dx
    - Channel 3: Spatial gradient dz/dy
    - Channel 4: Spatially broadcast rainfall rate (r_t - drain) [mm/hr]

    Output channel (1):
    - Predicted depth increment delta_h: h_{t+1} = max(0, h_t + delta_h)
    """

    def __init__(
        self,
        in_channels: int = 5,
        out_channels: int = 1,
        base_features: int = 32,
    ) -> None:
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.base_features = base_features
        raise NotImplementedError(
            "Planned for Phase 4: UNetSurrogate architecture definition using PyTorch."
        )

    def forward(self, x: Any) -> Any:
        """Forward pass predicting delta depth tensor."""
        raise NotImplementedError("Planned for Phase 4: UNetSurrogate forward pass.")


class ConservativeSurrogate:
    """Flux-conservative neural surrogate guaranteeing strict mass conservation.

    Instead of directly predicting depth increments, this network predicts inter-cell
    mass fluxes (Q_x, Q_y) on cell edges, enforcing:
        h_{t+1} = h_t - dt/dx * (div Q) + source - sink
    """

    def __init__(
        self,
        in_channels: int = 5,
        base_features: int = 32,
    ) -> None:
        self.in_channels = in_channels
        self.base_features = base_features
        raise NotImplementedError(
            "Planned for Phase 5: ConservativeSurrogate flux-based architecture."
        )

    def forward(self, x: Any) -> Any:
        """Forward pass predicting edge volumetric fluxes."""
        raise NotImplementedError("Planned for Phase 5: ConservativeSurrogate forward pass.")

