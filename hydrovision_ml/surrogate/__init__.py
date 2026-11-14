"""Neural surrogate architecture, loss functions, training, and rollout subpackage.

Phase: Phase 4 & 5 (Surrogate & Physics Loss)
Owner: ML Teammate
"""

from hydrovision_ml.surrogate.losses import (
    AccuracyMeter,
    WeightedHuberLoss,
    mass_conservation_loss,
    nonneg_penalty,
    rollout_loss,
)
from hydrovision_ml.surrogate.model import (
    ConservativeSurrogate,
    Normalizer,
    UNetSurrogate,
)
from hydrovision_ml.surrogate.rollout import rollout, rollout_batched

__all__ = [
    "UNetSurrogate",
    "ConservativeSurrogate",
    "Normalizer",
    "AccuracyMeter",
    "WeightedHuberLoss",
    "mass_conservation_loss",
    "nonneg_penalty",
    "rollout_loss",
    "rollout",
    "rollout_batched",
]

