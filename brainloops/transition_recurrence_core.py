from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.decomposition import PCA

def _as_matrix(Z: np.ndarray, *, name: str = "block") -> np.ndarray:
    Z = np.asarray(Z, dtype=float)
    if Z.ndim != 2 or Z.shape[0] < 1 or Z.shape[1] < 1:
        raise ValueError(f"{name} must be a non-empty 2-D array")
    if not np.all(np.isfinite(Z)):
        raise ValueError(f"{name} contains non-finite values")
    return Z


def lag_grid(
    epoch_s: float = 0.5,
    min_s: float = 2.0,
    max_s: float = 20.0,
    step_s: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    if epoch_s <= 0 or min_s <= 0 or max_s < min_s or step_s <= 0:
        raise ValueError("invalid lag grid parameters")
    n_steps_f = (max_s - min_s) / step_s
    if not np.isclose(n_steps_f, round(n_steps_f), atol=1e-10):
        raise ValueError("lag range must align to the requested step")
    lags_s = min_s + np.arange(int(round(n_steps_f)) + 1, dtype=float) * step_s
    lag_epochs_f = lags_s / epoch_s
    if not np.allclose(lag_epochs_f, np.round(lag_epochs_f), atol=1e-10):
        raise ValueError("lag grid is not exactly representable on the epoch grid")
    step_epochs_f = step_s / epoch_s
    if not np.isclose(step_epochs_f, round(step_epochs_f), atol=1e-10):
        raise ValueError("lag step is not exactly representable on the epoch grid")
    return lags_s, np.round(lag_epochs_f).astype(int)


def transition_vectors(Z: np.ndarray, half_window: int = 1) -> np.ndarray:
    Z = _as_matrix(Z)
    if half_window < 1:
        raise ValueError("half_window must be at least 1")
    if Z.shape[0] <= 2 * half_window:
        raise ValueError("block is too short for the transition window")
    vectors = []
    for center in range(half_window, Z.shape[0] - half_window):
        before = Z[center - half_window : center].mean(axis=0)
        after = Z[center + 1 : center + half_window + 1].mean(axis=0)
        vectors.append(after - before)
    return np.asarray(vectors, dtype=float)


def _validate_lags(lag_epochs: np.ndarray) -> np.ndarray:
    lag_epochs = np.asarray(lag_epochs)
    if lag_epochs.ndim != 1 or lag_epochs.size < 1:
        raise ValueError("lag_epochs must be a non-empty 1-D array")
    if not np.all(np.isfinite(lag_epochs)):
        raise ValueError("lag_epochs contains non-finite values")
    rounded = np.round(lag_epochs).astype(int)
    if not np.allclose(lag_epochs, rounded) or np.any(rounded < 1):
        raise ValueError("lag_epochs must contain positive integers")
    return rounded


def _transition_spectrum_from_vectors(
    vector_blocks: Sequence[np.ndarray], lag_epochs: np.ndarray
) -> np.ndarray:
    lags = _validate_lags(lag_epochs)
    if not vector_blocks:
        raise ValueError("at least one block is required")
    per_block = []
    max_lag = int(lags.max())
    for block in vector_blocks:
        V = _as_matrix(block, name="transition block")
        if V.shape[0] <= max_lag:
            raise ValueError("transition block is too short for requested lag")
        scores = []
        norms = np.linalg.norm(V, axis=1)
        for lag in lags:
            a = V[:-lag]
            b = V[lag:]
            valid = (norms[:-lag] > 0) & (norms[lag:] > 0)
            if not np.any(valid):
                raise ValueError("transition block has no nonzero vector pairs at requested lag")
            cosine = np.sum(a[valid] * b[valid], axis=1) / (
                norms[:-lag][valid] * norms[lag:][valid]
            )
            scores.append(float(np.median(cosine)))
        per_block.append(scores)
    return np.median(np.asarray(per_block, dtype=float), axis=0)


def transition_recurrence_spectrum(
    blocks: Sequence[np.ndarray],
    lag_epochs: np.ndarray,
    half_window: int = 1,
) -> np.ndarray:
    return _transition_spectrum_from_vectors(
        [transition_vectors(block, half_window=half_window) for block in blocks],
        lag_epochs,
    )


def state_recurrence_spectrum(
    blocks: Sequence[np.ndarray], lag_epochs: np.ndarray
) -> np.ndarray:
    lags = _validate_lags(lag_epochs)
    if not blocks:
        raise ValueError("at least one block is required")
    max_lag = int(lags.max())
    per_block = []
    for block in blocks:
        Z = _as_matrix(block)
        if Z.shape[0] <= max_lag:
            raise ValueError("state block is too short for requested lag")
        scores = []
        for lag in lags:
            d2 = np.sum((Z[:-lag] - Z[lag:]) ** 2, axis=1)
            scores.append(-float(np.median(d2)))
        per_block.append(scores)
    return np.median(np.asarray(per_block, dtype=float), axis=0)


def fit_standardized_pca_blocks(
    blocks: Sequence[np.ndarray], pca_dim: int = 8
) -> tuple[np.ndarray, ...]:
    if not blocks:
        raise ValueError("at least one block is required")
    if pca_dim < 1:
        raise ValueError("pca_dim must be positive")
    matrices = tuple(_as_matrix(block) for block in blocks)
    n_features = matrices[0].shape[1]
    if any(block.shape[1] != n_features for block in matrices):
        raise ValueError("all blocks must have the same feature dimension")
    pooled = np.vstack(matrices)
    if not np.any(np.ptp(pooled, axis=0) > 0):
        raise ValueError("PCA component variance is zero or degenerate")
    n_components = min(int(pca_dim), n_features, pooled.shape[0] - 1)
    if n_components < 1:
        raise ValueError("not enough epochs for PCA")
    pca = PCA(n_components=n_components, svd_solver="full")
    pca.fit(pooled)
    transformed = tuple(pca.transform(block) for block in matrices)
    pooled_scores = np.vstack(transformed)
    scale = pooled_scores.std(axis=0, ddof=0)
    if not np.all(np.isfinite(scale)) or np.any(scale <= 1e-12):
        raise ValueError("PCA component variance is zero or degenerate")
    return tuple(scores / scale for scores in transformed)


def max_recurrence(spectrum: np.ndarray, lags_s: np.ndarray) -> tuple[float, float]:
    spectrum = np.asarray(spectrum, dtype=float)
    lags_s = np.asarray(lags_s, dtype=float)
    if spectrum.ndim != 1 or lags_s.ndim != 1 or spectrum.shape != lags_s.shape or spectrum.size == 0:
        raise ValueError("spectrum and lags_s must be equally sized non-empty vectors")
    if not np.all(np.isfinite(spectrum)) or not np.all(np.isfinite(lags_s)):
        raise ValueError("spectrum and lags_s must be finite")
    index = int(np.argmax(spectrum))
    return float(spectrum[index]), float(lags_s[index])
