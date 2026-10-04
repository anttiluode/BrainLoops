from __future__ import annotations

import numpy as np

from .circulation import asymmetry_index, transition_counts


def reversible_markov_samples(
    N: np.ndarray,
    n_steps: int,
    n_null: int,
    rng: np.random.Generator,
) -> np.ndarray:
    N = np.asarray(N, dtype=float)
    if N.ndim != 2 or N.shape[0] != N.shape[1]:
        raise ValueError("N must be square")
    if n_steps < 1 or n_null < 1:
        raise ValueError("n_steps and n_null must be positive")
    sym = (N + N.T) / 2.0
    rows = sym.sum(axis=1)
    support = np.flatnonzero(rows > 0)
    if support.size == 0:
        return np.zeros(n_null, dtype=float)

    P = np.zeros_like(sym)
    P[support] = sym[support] / rows[support, None]
    pi = rows[support] / rows[support].sum()
    cumulative = np.cumsum(P, axis=1)
    out = np.empty(n_null, dtype=float)
    for r in range(n_null):
        seq = np.empty(n_steps, dtype=int)
        seq[0] = int(rng.choice(support, p=pi))
        uniforms = rng.random(n_steps)
        for t in range(1, n_steps):
            nxt = int(np.searchsorted(cumulative[seq[t - 1]], uniforms[t], side="right"))
            seq[t] = min(nxt, N.shape[0] - 1)
        out[r] = asymmetry_index(transition_counts(seq, N.shape[0]))
    return out


def phase_surrogate(Z: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    Z = np.asarray(Z, dtype=float)
    if Z.ndim != 2 or Z.shape[0] < 3:
        raise ValueError("Z must be epochs x dimensions with at least three epochs")
    T = Z.shape[0]
    F = np.fft.rfft(Z, axis=0)
    phase = rng.uniform(0.0, 2.0 * np.pi, F.shape[0])
    phase[0] = 0.0
    if T % 2 == 0:
        phase[-1] = 0.0
    rotated = F * np.exp(1j * phase)[:, None]
    return np.fft.irfft(rotated, n=T, axis=0)
