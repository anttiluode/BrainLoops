from __future__ import annotations

import numpy as np

from .types import CycleSummary, VisitSequence


def transition_counts(seq: np.ndarray, k: int) -> np.ndarray:
    seq = np.asarray(seq, dtype=int)
    if seq.ndim != 1:
        raise ValueError("seq must be 1-D")
    if k < 1:
        raise ValueError("k must be positive")
    N = np.zeros((k, k), dtype=float)
    if seq.size < 2:
        return N
    if np.any(seq < 0) or np.any(seq >= k):
        raise ValueError("state label outside [0, k)")
    np.add.at(N, (seq[:-1], seq[1:]), 1.0)
    return N


def asymmetry_index(N: np.ndarray) -> float:
    N = np.asarray(N, dtype=float)
    if N.ndim != 2 or N.shape[0] != N.shape[1]:
        raise ValueError("N must be square")
    denom = float((N + N.T).sum())
    return 0.0 if denom == 0.0 else float(np.abs(N - N.T).sum() / denom)


def top_three_cycles(
    N: np.ndarray,
    visits: VisitSequence,
    epoch_s: float,
    n: int = 5,
) -> tuple[CycleSummary, ...]:
    N = np.asarray(N, dtype=float)
    F = N - N.T
    k = N.shape[0]
    candidates: list[tuple[float, tuple[int, int, int]]] = []
    for i in range(k):
        for j in range(k):
            for l in range(k):
                if i < j and i < l and j != l:
                    flux = float(F[i, j] + F[j, l] + F[l, i])
                    if flux > 0:
                        candidates.append((flux, (i, j, l)))
    candidates.sort(key=lambda item: item[0], reverse=True)

    out: list[CycleSummary] = []
    seq = visits.labels
    starts = visits.starts
    for flux, (i, j, l) in candidates[:n]:
        periods: list[float] = []
        positions = np.flatnonzero(seq == i)
        for a, b in zip(positions[:-1], positions[1:]):
            middle = list(seq[a + 1 : b])
            if j not in middle:
                continue
            jpos = middle.index(j)
            if l in middle[jpos + 1 :]:
                periods.append(float((starts[b] - starts[a]) * epoch_s))
        out.append(
            CycleSummary(
                cycle=(i, j, l),
                net_flux=flux,
                full_rounds=len(periods),
                period_s=float(np.median(periods)) if periods else None,
            )
        )
    return tuple(out)


def return_times(labels: np.ndarray, epoch_s: float) -> np.ndarray:
    labels = np.asarray(labels, dtype=int)
    if labels.ndim != 1:
        raise ValueError("labels must be 1-D")
    if epoch_s <= 0:
        raise ValueError("epoch_s must be positive")
    times: list[float] = []
    for state in np.unique(labels):
        idx = np.flatnonzero(labels == state)
        gaps = np.diff(idx)
        times.extend((gaps[gaps > 1] * epoch_s).astype(float).tolist())
    return np.asarray(times, dtype=float)
