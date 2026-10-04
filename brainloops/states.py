from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from .types import StatePartition, VisitSequence


def fit_states(Z: np.ndarray, k: int, seed: int = 0) -> StatePartition:
    Z = np.asarray(Z, dtype=float)
    if Z.ndim != 2 or len(Z) < 2:
        raise ValueError("Z must be a 2-D trajectory with at least two epochs")
    if not 2 <= k < len(Z):
        raise ValueError("k must be at least 2 and smaller than the number of epochs")
    km = KMeans(n_clusters=k, random_state=seed, n_init=1).fit(Z)
    return StatePartition(labels=km.labels_.copy(), centers=km.cluster_centers_.copy(), k=k)


def collapse_visits(labels: np.ndarray) -> VisitSequence:
    labels = np.asarray(labels, dtype=int)
    if labels.ndim != 1 or labels.size == 0:
        raise ValueError("labels must be a non-empty 1-D array")
    change = np.r_[True, labels[1:] != labels[:-1]]
    starts = np.flatnonzero(change)
    return VisitSequence(labels=labels[change], starts=starts)
