from __future__ import annotations

from dataclasses import asdict
from math import ceil
from pathlib import Path
from typing import Sequence

import numpy as np
from sklearn.decomposition import PCA

from .circulation import asymmetry_index, top_three_cycles, transition_counts
from .dynamics import fit_linear_dynamics, summarize_modes
from .io import load_edf_features
from .nulls import phase_surrogate, reversible_markov_samples
from .states import collapse_visits, fit_states
from .types import FeatureBatch, KRecurrenceResult, RecurrenceClass

DEFAULT_KS = (6, 10, 14, 20)
SURROGATE_MARKOV_N_NULL = 9


def classify_recurrence(
    rows: Sequence[KRecurrenceResult],
    alpha: float = 0.05,
    required_fraction: float = 2 / 3,
) -> RecurrenceClass:
    if not rows:
        raise ValueError("rows must not be empty")
    if not 0 < required_fraction <= 1:
        raise ValueError("required_fraction must be in (0, 1]")
    need = max(2, ceil(required_fraction * len(rows)))
    markov = sum(row.p_markov <= alpha for row in rows)
    both = sum(row.p_markov <= alpha and row.p_surrogate <= alpha for row in rows)
    if both >= need:
        return "BEYOND_LINEAR_RECURRENCE"
    if markov >= need:
        return "LINEAR_LAG_RECURRENCE"
    return "NO_ROBUST_RECURRENCE"


def _recurrence_rows(
    Z: np.ndarray,
    epoch_s: float,
    ks: Sequence[int],
    n_null: int,
    seed: int,
) -> tuple[KRecurrenceResult, ...]:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    rng = np.random.default_rng(seed)
    surrogates = [phase_surrogate(Z, rng) for _ in range(n_null)]
    rows: list[KRecurrenceResult] = []
    for k in (int(value) for value in ks):
        if not 2 <= k < len(Z):
            continue
        partition = fit_states(Z, k=k, seed=seed)
        visits = collapse_visits(partition.labels)
        N = transition_counts(visits.labels, k)
        A = asymmetry_index(N)
        markov = reversible_markov_samples(N, len(visits.labels), n_null, rng)
        markov_sd = float(markov.std())
        excess_z = float((A - markov.mean()) / (markov_sd + 1e-9))
        p_markov = float((1 + np.sum(markov >= A)) / (1 + n_null))

        surrogate_z: list[float] = []
        for surrogate in surrogates:
            sp = fit_states(surrogate, k=k, seed=seed)
            sv = collapse_visits(sp.labels)
            Ns = transition_counts(sv.labels, k)
            own = reversible_markov_samples(Ns, len(sv.labels), SURROGATE_MARKOV_N_NULL, rng)
            surrogate_z.append(float((asymmetry_index(Ns) - own.mean()) / (own.std() + 1e-9)))
        sz = np.asarray(surrogate_z, dtype=float)
        p_surrogate = float((1 + np.sum(sz >= excess_z)) / (1 + n_null))
        rows.append(
            KRecurrenceResult(
                k=k,
                asymmetry=float(A),
                markov_mean=float(markov.mean()),
                markov_sd=markov_sd,
                p_markov=p_markov,
                excess_z=excess_z,
                surrogate_mean=float(sz.mean()),
                surrogate_sd=float(sz.std()),
                p_surrogate=p_surrogate,
                n_visits=len(visits.labels),
                cycles=top_three_cycles(N, visits, epoch_s=epoch_s),
            )
        )
    if not rows:
        raise ValueError("no valid k values for trajectory length")
    return tuple(rows)


def probe_features(
    features: FeatureBatch,
    ks: Sequence[int] = DEFAULT_KS,
    dim: int = 8,
    n_null: int = 19,
    seed: int = 0,
) -> dict[str, object]:
    X = np.asarray(features.X, dtype=float)
    if X.ndim != 2 or len(X) < 3:
        raise ValueError("feature trajectory is too short")
    n_dim = min(int(dim), X.shape[1], X.shape[0] - 1)
    Z = PCA(n_components=n_dim).fit_transform(X)
    rows = _recurrence_rows(Z, features.epoch_s, ks=ks, n_null=n_null, seed=seed)
    fit = fit_linear_dynamics(Z)
    modes = summarize_modes(fit, features.epoch_s)
    return {
        "artifact_stats": None if features.artifact_stats is None else asdict(features.artifact_stats),
        "discrete": {
            "classification": classify_recurrence(rows),
            "rows": [asdict(row) for row in rows],
        },
        "continuous": {
            "train_r2": fit.train_r2,
            "modes": [
                {
                    "eigenvalue": {"real": mode.eigenvalue.real, "imag": mode.eigenvalue.imag},
                    "magnitude": mode.magnitude,
                    "angle_rad": mode.angle_rad,
                    "decay_epochs": mode.decay_epochs,
                    "period_s": mode.period_s,
                }
                for mode in modes
            ],
        },
    }


def probe_edf(
    path: str | Path,
    region: str = "All",
    epoch_s: float = 0.5,
    fs: float = 100.0,
    ks: Sequence[int] = DEFAULT_KS,
    dim: int = 8,
    n_null: int = 19,
    seed: int = 0,
) -> dict[str, object]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    features = load_edf_features(path, region=region, epoch_s=epoch_s, fs=fs)
    payload = probe_features(features, ks=ks, dim=dim, n_null=n_null, seed=seed)
    payload["recording"] = str(path)
    payload["region"] = region
    return payload
