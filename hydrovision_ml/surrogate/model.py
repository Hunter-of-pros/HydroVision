"""Neural network surrogate architectures and normalizer for urban flood forecasting.

Architectures:
- Normalizer: Standardizes multi-modal spatial inputs, terrain, and rainfall scalars.
- UNetSurrogate: 2D U-Net taking [h_t, h_{t-1}, dem, slope_x, slope_y, rain_t, drain_cap] -> delta_depth
- ConservativeSurrogate: Flux-conserving surrogate placeholder for Phase 5

Phase: Phase 4 (Baseline Surrogate)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn


class Normalizer:
    """Multi-modal normalizer for water depth, terrain topography, and storm parameters.

    Scaling rules (per Contract & Step 2 spec):
    - Depth: scaled by fixed reference 1.5 m (NOT a z-score)
    - DEM & Slopes: standardized with terrain dataset mean and std
    - Rain: divided by 150.0 mm/hr
    - Drain capacity: divided by 30.0 mm/hr
    - Target: depth increment (h_{t+1} - h_t) divided by training-set delta std
    """

    def __init__(
        self,
        depth_scale_m: float = 1.5,
        rain_scale_mmhr: float = 150.0,
        drain_scale_mmhr: float = 30.0,
        dem_mean: float = 878.40,
        dem_std: float = 7.55,
        slope_x_mean: float = -0.0013,
        slope_x_std: float = 0.0175,
        slope_y_mean: float = -0.0006,
        slope_y_std: float = 0.0183,
        target_delta_std: float = 0.00372,
    ) -> None:
        self.depth_scale_m = float(depth_scale_m)
        self.rain_scale_mmhr = float(rain_scale_mmhr)
        self.drain_scale_mmhr = float(drain_scale_mmhr)
        self.dem_mean = float(dem_mean)
        self.dem_std = float(max(1e-4, dem_std))
        self.slope_x_mean = float(slope_x_mean)
        self.slope_x_std = float(max(1e-4, slope_x_std))
        self.slope_y_mean = float(slope_y_mean)
        self.slope_y_std = float(max(1e-4, slope_y_std))
        self.target_delta_std = float(max(1e-6, target_delta_std))

    @classmethod
    def fit_from_data(
        cls,
        terrain_path: str = "artifacts/data/terrain.npz",
        train_depth_path: str = r"C:\hydrovision_data\data\train\depth.npy",
        max_scenarios_for_std: int = 50,
    ) -> "Normalizer":
        """Compute normalization parameters directly from terrain and training set."""
        terrain = np.load(terrain_path)
        dem = terrain["dem_m"].astype(np.float32)
        dx = float(terrain["cell_size_m"])
        sy, sx = np.gradient(dem, dx)

        dem_mean = float(np.mean(dem))
        dem_std = float(np.std(dem))
        sx_mean = float(np.mean(sx))
        sx_std = float(np.std(sx))
        sy_mean = float(np.mean(sy))
        sy_std = float(np.std(sy))

        depth_mmap = np.load(train_depth_path, mmap_mode="r")
        num_sc = min(max_scenarios_for_std, depth_mmap.shape[0])
        deltas = []
        for i in range(num_sc):
            d = depth_mmap[i]  # (121, 64, 64)
            diff = np.diff(d, axis=0)  # (120, 64, 64)
            # Focus on non-zero depth changes
            non_zero = diff[np.abs(diff) > 1e-4]
            if len(non_zero) > 0:
                deltas.append(non_zero)

        if deltas:
            delta_std = float(np.std(np.concatenate(deltas)))
        else:
            delta_std = 0.00372

        return cls(
            depth_scale_m=1.5,
            rain_scale_mmhr=150.0,
            drain_scale_mmhr=30.0,
            dem_mean=dem_mean,
            dem_std=dem_std,
            slope_x_mean=sx_mean,
            slope_x_std=sx_std,
            slope_y_mean=sy_mean,
            slope_y_std=sy_std,
            target_delta_std=delta_std,
        )

    def normalize_depth(self, h: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return h / self.depth_scale_m

    def denormalize_depth(self, h_norm: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return h_norm * self.depth_scale_m

    def normalize_dem(self, dem: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return (dem - self.dem_mean) / self.dem_std

    def normalize_slope_x(self, sx: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return (sx - self.slope_x_mean) / self.slope_x_std

    def normalize_slope_y(self, sy: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return (sy - self.slope_y_mean) / self.slope_y_std

    def normalize_rain(self, rain_mmhr: Union[float, np.ndarray, torch.Tensor]) -> Union[float, np.ndarray, torch.Tensor]:
        return rain_mmhr / self.rain_scale_mmhr

    def normalize_drain(self, drain_mmhr: Union[float, np.ndarray, torch.Tensor]) -> Union[float, np.ndarray, torch.Tensor]:
        return drain_mmhr / self.drain_scale_mmhr

    def normalize_delta(self, delta: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return delta / self.target_delta_std

    def denormalize_delta(self, delta_norm: Union[np.ndarray, torch.Tensor]) -> Union[np.ndarray, torch.Tensor]:
        return delta_norm * self.target_delta_std

    def to_dict(self) -> Dict[str, float]:
        return {
            "depth_scale_m": self.depth_scale_m,
            "rain_scale_mmhr": self.rain_scale_mmhr,
            "drain_scale_mmhr": self.drain_scale_mmhr,
            "dem_mean": self.dem_mean,
            "dem_std": self.dem_std,
            "slope_x_mean": self.slope_x_mean,
            "slope_x_std": self.slope_x_std,
            "slope_y_mean": self.slope_y_mean,
            "slope_y_std": self.slope_y_std,
            "target_delta_std": self.target_delta_std,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Normalizer":
        return cls(**data)

    def save(self, path: str = "artifacts/models/normalizer.json") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str = "artifacts/models/normalizer.json") -> "Normalizer":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


class DoubleConv(nn.Module):
    """Double convolution block with reflection padding, BatchNorm, and ReLU."""

    def __init__(self, in_ch: int, out_ch: int, padding_mode: str = "reflect") -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, padding_mode=padding_mode, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, padding_mode=padding_mode, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class UNetSurrogate(nn.Module):
    """Compact 2D U-Net neural surrogate predicting water depth increments.

    Channels:
    - Default input channels (7): [h_t, h_{t-1}, dem, slope_x, slope_y, rain_t, drain_cap]
    - Output channels (1): delta_h (normalized increment)
    - Next depth: max(h_t + delta_norm * delta_std, 0.0)
    - Boundary padding: reflection padding ('reflect') to prevent border edge accumulation.
    """

    def __init__(
        self,
        in_channels: int = 7,
        out_channels: int = 1,
        base_ch: int = 26,
        padding_mode: str = "reflect",
        steps_per_pass: int = 1,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.base_ch = base_ch
        self.padding_mode = padding_mode
        self.steps_per_pass = steps_per_pass

        # Encoder
        self.inc = DoubleConv(in_channels, base_ch, padding_mode=padding_mode)
        self.down1 = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(base_ch, base_ch * 2, padding_mode=padding_mode),
        )
        self.down2 = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(base_ch * 2, base_ch * 4, padding_mode=padding_mode),
        )

        # Decoder with skip connections
        self.up1 = nn.ConvTranspose2d(base_ch * 4, base_ch * 2, kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv(base_ch * 4, base_ch * 2, padding_mode=padding_mode)
        self.up2 = nn.ConvTranspose2d(base_ch * 2, base_ch, kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv(base_ch * 2, base_ch, padding_mode=padding_mode)

        # Output head
        self.outc = nn.Conv2d(base_ch, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass predicting normalized depth increment delta."""
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

    def predict_next(
        self,
        h_t: torch.Tensor,
        x: torch.Tensor,
        target_delta_std: float,
    ) -> torch.Tensor:
        """Step prediction enforcing physical non-negativity constraint."""
        delta_norm = self.forward(x)
        delta_m = delta_norm * target_delta_std
        return torch.clamp(h_t + delta_m, min=0.0)


class ConservativeSurrogate(nn.Module):
    """Flux-conservative neural surrogate placeholder for Phase 5."""

    def __init__(self, in_channels: int = 7, base_features: int = 32) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.base_features = base_features

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError("Planned for Phase 5: ConservativeSurrogate flux-based architecture.")
