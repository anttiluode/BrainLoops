from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brainloops import __version__
from brainloops.circulation import asymmetry_index, top_three_cycles, transition_counts
from brainloops.features import robust_scale_clip
from brainloops.nulls import phase_surrogate, reversible_markov_samples
from brainloops.probe import SURROGATE_MARKOV_N_NULL, classify_recurrence
from brainloops.receipts import config_fingerprint, write_receipt
from brainloops.states import collapse_visits, fit_states
from brainloops.types import KRecurrenceResult, RecurrenceClass

KS = (6, 10, 20)
EXPECTED: dict[str, RecurrenceClass] = {
    "reversible_ar_noise": "NO_ROBUST_RECURRENCE",
    "linear_rotating_ar": "LINEAR_LAG_RECURRENCE",
    "smooth_forward_phase": "LINEAR_LAG_RECURRENCE",
    "event_switching_loop": "BEYOND_LINEAR_RECURRENCE",
}


def _synthetic_cases(seed: int, T: int = 2400, D: int = 40) -> dict[str, np.ndarray]:
    # Keep the predecessor probe's generator order exactly: Gate 0 is a
    # regression test for its four planted truth classes, not a new benchmark.
    rng = np.random.default_rng(seed)
    noise = np.zeros((T, D), dtype=float)
    for t in range(1, T):
        noise[t] = 0.9 * noise[t - 1] + rng.standard_normal(D)

    phase = np.cumsum(2 * np.pi / 12 + 0.3 * rng.standard_normal(T))
    W = rng.standard_normal((3, D))
    smooth = np.c_[np.cos(phase), np.sin(phase)] @ W[:2] + noise

    theta = 2 * np.pi / 12
    R = 0.95 * np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    y = np.zeros((T, 2), dtype=float)
    for t in range(1, T):
        y[t] = R @ y[t - 1] + rng.standard_normal(2)
    linear = y @ W[:2] + noise

    state = np.zeros(T, dtype=int)
    cur = 0
    for t in range(T):
        if rng.random() < 0.25:
            cur = (cur + 1) % 3
        state[t] = cur
    event = 2.0 * rng.standard_normal((3, D))[state] + noise

    return {
        "reversible_ar_noise": noise,
        "linear_rotating_ar": linear,
        "smooth_forward_phase": smooth,
        "event_switching_loop": event,
    }


def _measure_case(X: np.ndarray, seed: int, n_null: int) -> tuple[KRecurrenceResult, ...]:
    rng = np.random.default_rng(seed)
    X, _ = robust_scale_clip(X)
    Z = PCA(n_components=min(8, X.shape[1]), random_state=seed).fit_transform(X)
    surrogates = [phase_surrogate(Z, rng) for _ in range(n_null)]
    rows: list[KRecurrenceResult] = []
    for k in KS:
        partition = fit_states(Z, k, seed=seed)
        visits = collapse_visits(partition.labels)
        N = transition_counts(visits.labels, k)
        A = asymmetry_index(N)
        markov = reversible_markov_samples(N, len(visits.labels), n_null, rng)
        p_markov = (1 + int(np.sum(markov >= A))) / (1 + len(markov))
        markov_sd = float(markov.std())
        excess_z = float((A - markov.mean()) / (markov_sd + 1e-9))

        surrogate_z: list[float] = []
        for S in surrogates:
            sp = fit_states(S, k, seed=seed)
            sv = collapse_visits(sp.labels)
            Ns = transition_counts(sv.labels, k)
            As = asymmetry_index(Ns)
            own_null = reversible_markov_samples(Ns, len(sv.labels), SURROGATE_MARKOV_N_NULL, rng)
            surrogate_z.append(float((As - own_null.mean()) / (own_null.std() + 1e-9)))
        sz = np.asarray(surrogate_z)
        p_surrogate = (1 + int(np.sum(sz >= excess_z))) / (1 + len(sz))
        rows.append(
            KRecurrenceResult(
                k=k,
                asymmetry=float(A),
                markov_mean=float(markov.mean()),
                markov_sd=markov_sd,
                p_markov=float(p_markov),
                excess_z=excess_z,
                surrogate_mean=float(sz.mean()),
                surrogate_sd=float(sz.std()),
                p_surrogate=float(p_surrogate),
                n_visits=int(len(visits.labels)),
                cycles=top_three_cycles(N, visits, epoch_s=0.5),
            )
        )
    return tuple(rows)


def run_gate0(seed: int = 1, n_null: int = 99) -> dict[str, object]:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    config = {"seed": seed, "n_null": n_null, "surrogate_markov_n_null": SURROGATE_MARKOV_N_NULL, "ks": list(KS), "epochs": 2400, "dims": 40, "code_version": __version__}
    cases: dict[str, object] = {}
    for name, X in _synthetic_cases(seed).items():
        # The predecessor truth probe used analysis seed 0 for every case.
        rows = _measure_case(X, seed=0, n_null=n_null)
        classification = classify_recurrence(rows)
        cases[name] = {
            "classification": classification,
            "expected": EXPECTED[name],
            "rows": [asdict(row) for row in rows],
        }
    status = "PASS" if all(item["classification"] == item["expected"] for item in cases.values()) else "FAIL"
    return {
        "gate": "gate0_synthetic",
        "status": status,
        "config": config,
        "config_fingerprint": config_fingerprint(config),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--n-null", type=int, default=99)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run_gate0(seed=args.seed, n_null=args.n_null)
    write_receipt(args.output, receipt)
    for name, item in receipt["cases"].items():
        print(f"{name}: {item['classification']} (expected {item['expected']})")
    print(receipt["status"])
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
