from __future__ import annotations

import numpy as np

from .types import LinearDynamicsFit, ModeSummary


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    residual = float(np.sum((y_true - y_pred) ** 2))
    centered = y_true - np.mean(y_true, axis=0, keepdims=True)
    total = float(np.sum(centered**2))
    if total <= 1e-15:
        return 1.0 if residual <= 1e-15 else 0.0
    return 1.0 - residual / total


def fit_linear_dynamics(Z: np.ndarray, ridge: float = 1e-3) -> LinearDynamicsFit:
    Z = np.asarray(Z, dtype=float)
    if Z.ndim != 2 or Z.shape[0] < 3 or Z.shape[1] < 1:
        raise ValueError("Z must be epochs x dimensions with at least three epochs")
    if not np.all(np.isfinite(Z)):
        raise ValueError("Z contains non-finite values")
    if ridge < 0:
        raise ValueError("ridge must be non-negative")
    X = Z[:-1]
    Y = Z[1:]
    gram = X.T @ X + ridge * np.eye(X.shape[1])
    B = np.linalg.solve(gram, X.T @ Y)
    A = B.T
    pred = X @ B
    eigenvalues, eigenvectors = np.linalg.eig(A)
    return LinearDynamicsFit(
        A=A,
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        train_r2=float(_r2(Y, pred)),
    )


def score_linear_dynamics(fit: LinearDynamicsFit, Z: np.ndarray) -> float:
    Z = np.asarray(Z, dtype=float)
    if Z.ndim != 2 or Z.shape[0] < 2 or Z.shape[1] != fit.A.shape[0]:
        raise ValueError("Z has incompatible shape")
    pred = Z[:-1] @ fit.A.T
    return float(_r2(Z[1:], pred))


def summarize_modes(fit: LinearDynamicsFit, epoch_s: float) -> tuple[ModeSummary, ...]:
    if epoch_s <= 0:
        raise ValueError("epoch_s must be positive")
    summaries: list[ModeSummary] = []
    for value in fit.eigenvalues:
        value = complex(value)
        magnitude = float(abs(value))
        angle = float(np.angle(value))
        if abs(angle) < 1e-8:
            angle = 0.0
            period_s = None
        else:
            period_s = float((2.0 * np.pi / abs(angle)) * epoch_s)
        decay_epochs = (
            float(-1.0 / np.log(magnitude))
            if 0.0 < magnitude < 1.0 and not np.isclose(magnitude, 1.0)
            else None
        )
        summaries.append(
            ModeSummary(
                eigenvalue=value,
                magnitude=magnitude,
                angle_rad=angle,
                decay_epochs=decay_epochs,
                period_s=period_s,
            )
        )
    summaries.sort(key=lambda item: item.magnitude, reverse=True)
    return tuple(summaries)
