from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import numpy as np
from sklearn.decomposition import PCA

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brainloops import __version__
from brainloops.circulation import return_times
from brainloops.datasets.eegmmidb import (
    MalformedAnnotationsError,
    MissingAnnotationsError,
    discover_runs,
    load_run,
)
from brainloops.receipts import config_fingerprint, write_receipt
from brainloops.states import fit_states
from brainloops.types import ClockValidationResult, EventSeries, FeatureBatch

KS = (6, 10, 20)
PERIOD_MIN_S = 2.0
PERIOD_MAX_S = 20.0
CLOCK_BAND_FRACTION = 0.20


def clock_alignment_score(
    recurrence_periods_s: np.ndarray,
    recurrence_weights: np.ndarray,
    event_onsets_s: np.ndarray,
) -> float:
    periods = np.asarray(recurrence_periods_s, dtype=float)
    weights = np.asarray(recurrence_weights, dtype=float)
    onsets = np.asarray(event_onsets_s, dtype=float)
    if periods.ndim != 1 or weights.ndim != 1 or periods.shape != weights.shape or periods.size == 0:
        raise ValueError("recurrence periods and weights must be aligned non-empty 1-D arrays")
    if np.any(~np.isfinite(periods)) or np.any(periods <= 0) or np.any(~np.isfinite(weights)) or np.any(weights < 0):
        raise ValueError("recurrence periods/weights are invalid")
    total = float(weights.sum())
    if total <= 0:
        raise ValueError("recurrence weights must sum to a positive value")
    if onsets.ndim != 1 or onsets.size < 2 or np.any(~np.isfinite(onsets)):
        raise ValueError("at least two finite event onsets are required")
    gaps = np.diff(onsets)
    if np.any(gaps <= 0):
        raise ValueError("event onsets must be strictly increasing")

    masses = []
    for gap in gaps:
        lo = (1.0 - CLOCK_BAND_FRACTION) * gap
        hi = (1.0 + CLOCK_BAND_FRACTION) * gap
        masses.append(float(weights[(periods >= lo) & (periods <= hi)].sum()) / total)
    return float(np.mean(masses))


def deterministic_subject_split(subjects: Sequence[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    unique = tuple(sorted({int(subject) for subject in subjects}))
    development = tuple(subject for subject in unique if subject % 5 == 0)
    heldout = tuple(subject for subject in unique if subject % 5 != 0)
    return development, heldout


def _t0_onsets(events: EventSeries) -> np.ndarray:
    onsets = np.asarray([event.onset_s for event in events.events if event.label == "T0"], dtype=float)
    if onsets.size < 3:
        raise MissingAnnotationsError("at least three T0 onsets are required for clock validation")
    return onsets


def _state_label_sets(
    features: FeatureBatch,
    ks: Sequence[int] = KS,
    dim: int = 8,
) -> tuple[np.ndarray, ...]:
    X = np.asarray(features.X, dtype=float)
    if X.ndim != 2 or len(X) < 20:
        raise ValueError("clock validation requires at least 20 feature epochs")
    n_dim = min(int(dim), X.shape[1], X.shape[0] - 1)
    if n_dim < 1:
        raise ValueError("no PCA dimensions available")
    Z = PCA(n_components=n_dim).fit_transform(X)
    label_sets = tuple(
        fit_states(Z, k=int(k), seed=0).labels
        for k in ks
        if 2 <= int(k) < len(Z)
    )
    if not label_sets:
        raise ValueError("no valid state coarse-grainings")
    return label_sets


def _periods_from_label_sets(
    label_sets: Sequence[np.ndarray],
    epoch_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    period_chunks: list[np.ndarray] = []
    raw_chunks: list[np.ndarray] = []
    for labels in label_sets:
        periods = return_times(labels, epoch_s)
        periods = periods[(periods >= PERIOD_MIN_S) & (periods <= PERIOD_MAX_S)]
        if periods.size:
            raw_chunks.append(periods)
    if not raw_chunks:
        raise ValueError("no recurrence periods in the preregistered 2-20 s range")
    n_sets = len(raw_chunks)
    weight_chunks: list[np.ndarray] = []
    for periods in raw_chunks:
        period_chunks.append(periods)
        weight_chunks.append(np.full(periods.size, 1.0 / (n_sets * periods.size), dtype=float))
    return np.concatenate(period_chunks), np.concatenate(weight_chunks)


def _measure_recurrence_periods(
    features: FeatureBatch,
    ks: Sequence[int] = KS,
    dim: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    return _periods_from_label_sets(_state_label_sets(features, ks=ks, dim=dim), features.epoch_s)


def _random_clock_same_span(onsets: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    onsets = np.asarray(onsets, dtype=float)
    if onsets.size < 3:
        raise ValueError("clock null requires at least three onsets")
    span = float(onsets[-1] - onsets[0])
    if span <= 0:
        raise ValueError("clock span must be positive")
    intervals = rng.dirichlet(np.ones(onsets.size - 1)) * span
    return onsets[0] + np.r_[0.0, np.cumsum(intervals)]


def evaluate_run_clock(
    features: FeatureBatch,
    events: EventSeries,
    subject: int,
    run: int,
    n_null: int = 99,
    seed: int = 0,
) -> ClockValidationResult:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    label_sets = _state_label_sets(features)
    periods, weights = _periods_from_label_sets(label_sets, features.epoch_s)
    t0 = _t0_onsets(events)
    score = clock_alignment_score(periods, weights, t0)
    rng = np.random.default_rng(seed)
    null_values: list[float] = []
    for _ in range(n_null):
        shuffled = tuple(rng.permutation(labels) for labels in label_sets)
        null_periods, null_weights = _periods_from_label_sets(shuffled, features.epoch_s)
        null_values.append(clock_alignment_score(null_periods, null_weights, t0))
    null_scores = np.asarray(null_values, dtype=float)
    p_value = (1 + int(np.sum(null_scores >= score))) / (1 + n_null)
    return ClockValidationResult(
        subject=int(subject),
        run=int(run),
        score=float(score),
        null_scores=null_scores,
        p_value=float(p_value),
        positive_direction=bool(score > np.median(null_scores)),
    )


def run_gate1(
    data: str | Path,
    subjects: Sequence[int] | None = None,
    n_null: int = 99,
    output: str | Path | None = None,
    resume: bool = False,
    seed: int = 0,
) -> dict[str, object]:
    root = Path(data)
    runs = [run for run in discover_runs(root, subjects=subjects) if 3 <= run.run <= 14]
    subject_ids = sorted({run.subject for run in runs})
    development, heldout = deterministic_subject_split(subject_ids)
    config = {
        "code_version": __version__,
        "data": str(root.resolve()),
        "subjects": subject_ids,
        "n_null": int(n_null),
        "seed": int(seed),
        "ks": list(KS),
        "period_range_s": [PERIOD_MIN_S, PERIOD_MAX_S],
        "clock_band_fraction": CLOCK_BAND_FRACTION,
    }
    fingerprint = config_fingerprint(config)
    output_path = None if output is None else Path(output)
    records: list[dict[str, object]] = []
    done: set[tuple[int, int]] = set()
    if resume and output_path is not None and output_path.exists():
        prior = json.loads(output_path.read_text(encoding="utf-8"))
        if prior.get("config_fingerprint") != fingerprint:
            raise ValueError("resume receipt config does not match current Gate 1 config")
        records = list(prior.get("runs", []))
        done = {(int(item["subject"]), int(item["run"])) for item in records if item.get("status") == "OK"}

    for run in runs:
        if (run.subject, run.run) in done:
            continue
        try:
            features, events = load_run(run)
            result = evaluate_run_clock(
                features,
                events,
                subject=run.subject,
                run=run.run,
                n_null=n_null,
                seed=seed + 1000 * run.subject + run.run,
            )
            record = {
                "status": "OK",
                **asdict(result),
                "artifact_stats": None if features.artifact_stats is None else asdict(features.artifact_stats),
            }
        except (MissingAnnotationsError, MalformedAnnotationsError, ValueError) as exc:
            record = {"status": "SKIP", "subject": run.subject, "run": run.run, "reason": str(exc)}
        records.append(record)
        if output_path is not None:
            write_receipt(
                output_path,
                {
                    "gate": "gate1_eegmmidb",
                    "status": "IN_PROGRESS",
                    "config": config,
                    "config_fingerprint": fingerprint,
                    "development_subjects": development,
                    "heldout_subjects": heldout,
                    "runs": records,
                },
            )

    successful = [item for item in records if item.get("status") == "OK"]
    subject_results: list[dict[str, object]] = []
    for subject in subject_ids:
        items = [item for item in successful if int(item["subject"]) == subject]
        if not items:
            continue
        score = float(np.median([float(item["score"]) for item in items]))
        null_matrix = np.asarray([item["null_scores"] for item in items], dtype=float)
        null_scores = np.median(null_matrix, axis=0)
        p_value = (1 + int(np.sum(null_scores >= score))) / (1 + len(null_scores))
        subject_results.append(
            {
                "subject": subject,
                "score": score,
                "null_scores": null_scores,
                "p_value": float(p_value),
                "positive_direction": bool(score > np.median(null_scores)),
                "n_runs": len(items),
            }
        )

    heldout_results = [item for item in subject_results if int(item["subject"]) in heldout]
    if n_null < 19 or len(heldout_results) < 3:
        status = "INSUFFICIENT_DATA"
        aggregate_p = None
        positive_fraction = None
    else:
        real_median = float(np.median([float(item["score"]) for item in heldout_results]))
        null_matrix = np.asarray([item["null_scores"] for item in heldout_results], dtype=float)
        aggregate_null = np.median(null_matrix, axis=0)
        aggregate_p = float((1 + int(np.sum(aggregate_null >= real_median))) / (1 + len(aggregate_null)))
        positive_fraction = float(np.mean([bool(item["positive_direction"]) for item in heldout_results]))
        status = "PASS" if aggregate_p <= 0.05 and positive_fraction >= 2 / 3 else "FAIL"

    receipt: dict[str, object] = {
        "gate": "gate1_eegmmidb",
        "status": status,
        "config": config,
        "config_fingerprint": fingerprint,
        "development_subjects": development,
        "heldout_subjects": heldout,
        "runs": records,
        "subjects": subject_results,
        "aggregate_p": aggregate_p,
        "positive_fraction": positive_fraction,
    }
    if output_path is not None:
        write_receipt(output_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BrainLoops against the EEGMMIDB task clock")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subjects", type=int, nargs="*")
    parser.add_argument("--n-null", type=int, default=99)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    receipt = run_gate1(
        data=args.data,
        subjects=args.subjects,
        n_null=args.n_null,
        output=args.output,
        resume=args.resume,
        seed=args.seed,
    )
    print(receipt["status"])
    return 0 if receipt["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
