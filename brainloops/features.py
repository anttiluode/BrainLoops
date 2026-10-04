from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy.signal import welch

from .types import ArtifactStats, FeatureBatch

DEFAULT_BANDS: dict[str, tuple[float, float]] = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


def robust_scale_clip(
    X: np.ndarray,
    clip: float = 4.0,
    epoch_extreme_fraction: float = 0.10,
) -> tuple[np.ndarray, ArtifactStats]:
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] < 1:
        raise ValueError("feature matrix must contain at least two epochs")
    if not np.all(np.isfinite(X)):
        raise ValueError("feature matrix contains non-finite values")
    if clip <= 0:
        raise ValueError("clip must be positive")
    if not 0 <= epoch_extreme_fraction <= 1:
        raise ValueError("epoch_extreme_fraction must be in [0, 1]")
    if np.all(np.ptp(X, axis=0) == 0):
        raise ValueError("feature matrix is constant")

    med = np.median(X, axis=0)
    mad = 1.4826 * np.median(np.abs(X - med), axis=0)
    scale = np.where(mad == 0, 1.0, mad)
    Z = (X - med) / scale
    extreme = np.abs(Z) > clip
    values_clipped = int(extreme.sum())
    per_epoch = extreme.mean(axis=1)
    epochs_over = int((per_epoch > epoch_extreme_fraction).sum())
    Y = np.clip(Z, -clip, clip)
    n_epochs, n_features = X.shape
    n_values = int(n_epochs * n_features)
    stats = ArtifactStats(
        n_epochs=n_epochs,
        n_values=n_values,
        values_clipped=values_clipped,
        fraction_values_clipped=values_clipped / n_values,
        epochs_over_extreme_fraction=epochs_over,
        fraction_epochs_over_extreme_fraction=epochs_over / n_epochs,
    )
    return Y, stats


def bandpower_epochs(
    data: np.ndarray,
    sfreq: float,
    epoch_s: float = 0.5,
    bands: Mapping[str, tuple[float, float]] | None = None,
) -> FeatureBatch:
    data = np.asarray(data, dtype=float)
    if data.ndim == 1:
        data = data[None, :]
    if data.ndim != 2 or data.shape[0] < 1:
        raise ValueError("data must be channels x samples")
    if sfreq <= 0 or epoch_s <= 0:
        raise ValueError("sfreq and epoch_s must be positive")
    if not np.all(np.isfinite(data)):
        raise ValueError("data contains non-finite values")

    samples_per_epoch = int(round(epoch_s * sfreq))
    if samples_per_epoch < 4:
        raise ValueError("epoch is too short for spectral estimation")
    n_epochs = data.shape[1] // samples_per_epoch
    if n_epochs < 2:
        raise ValueError("recording must contain at least two complete epochs")

    band_map = dict(DEFAULT_BANDS if bands is None else bands)
    trimmed = data[:, : n_epochs * samples_per_epoch]
    epochs = trimmed.reshape(data.shape[0], n_epochs, samples_per_epoch)
    rows: list[np.ndarray] = []
    for e in range(n_epochs):
        freqs, psd = welch(
            epochs[:, e, :],
            fs=sfreq,
            axis=-1,
            nperseg=samples_per_epoch,
            detrend="constant",
            scaling="density",
        )
        feats: list[np.ndarray] = []
        for ch in range(data.shape[0]):
            for low, high in band_map.values():
                mask = (freqs >= low) & (freqs < high)
                if not np.any(mask):
                    power = 0.0
                else:
                    power = float(np.trapezoid(psd[ch, mask], freqs[mask])) if mask.sum() > 1 else float(psd[ch, mask][0])
                feats.append(np.array(np.log1p(max(power, 0.0))))
        rows.append(np.asarray(feats, dtype=float))
    X = np.vstack(rows)
    feature_names = tuple(
        f"ch{ch}-{band}" for ch in range(data.shape[0]) for band in band_map
    )
    return FeatureBatch(X=X, epoch_s=float(epoch_s), feature_names=feature_names)
