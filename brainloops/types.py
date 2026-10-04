from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class ArtifactStats:
    n_epochs: int
    n_values: int
    values_clipped: int
    fraction_values_clipped: float
    epochs_over_extreme_fraction: int
    fraction_epochs_over_extreme_fraction: float


@dataclass(frozen=True)
class FeatureBatch:
    X: np.ndarray
    epoch_s: float
    feature_names: tuple[str, ...]
    artifact_stats: ArtifactStats | None = None


@dataclass(frozen=True)
class StatePartition:
    labels: np.ndarray
    centers: np.ndarray
    k: int


@dataclass(frozen=True)
class VisitSequence:
    labels: np.ndarray
    starts: np.ndarray


@dataclass(frozen=True)
class CycleSummary:
    cycle: tuple[int, int, int]
    net_flux: float
    full_rounds: int
    period_s: float | None


@dataclass(frozen=True)
class KRecurrenceResult:
    k: int
    asymmetry: float
    markov_mean: float
    markov_sd: float
    p_markov: float
    excess_z: float
    surrogate_mean: float
    surrogate_sd: float
    p_surrogate: float
    n_visits: int
    cycles: tuple[CycleSummary, ...]


RecurrenceClass = Literal[
    "NO_ROBUST_RECURRENCE",
    "LINEAR_LAG_RECURRENCE",
    "BEYOND_LINEAR_RECURRENCE",
]


@dataclass(frozen=True)
class LinearDynamicsFit:
    A: np.ndarray
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    train_r2: float


@dataclass(frozen=True)
class ModeSummary:
    eigenvalue: complex
    magnitude: float
    angle_rad: float
    decay_epochs: float | None
    period_s: float | None


@dataclass(frozen=True)
class EEGMMIDBRun:
    subject: int
    run: int
    path: Path


@dataclass(frozen=True)
class Event:
    onset_s: float
    label: str


@dataclass(frozen=True)
class EventSeries:
    events: tuple[Event, ...]


@dataclass(frozen=True)
class ClockValidationResult:
    subject: int
    run: int
    score: float
    null_scores: np.ndarray
    p_value: float
    positive_direction: bool
