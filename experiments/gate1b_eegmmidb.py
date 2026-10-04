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
NULL_NAME = "circular_annotation_shift_fixed_state_timeline"


def deterministic_subject_split(subjects: Sequence[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    unique = tuple(sorted({int(subject) for subject in subjects}))
    development = tuple(subject for subject in unique if subject % 5 == 0)
    heldout = tuple(subject for subject in unique if subject % 5 != 0)
    return development, heldout


def _t0_onsets(events: EventSeries) -> np.ndarray:
    onsets = np.asarray([event.onset_s for event in events.events if event.label == "T0"], dtype=float)
    if onsets.size < 3:
        raise MissingAnnotationsError("at least three T0 onsets are required for phase validation")
    if np.any(~np.isfinite(onsets)) or np.any(np.diff(onsets) <= 0):
        raise MalformedAnnotationsError("T0 onsets must be finite and strictly increasing")
    return onsets


def _state_label_sets(
    features: FeatureBatch,
    ks: Sequence[int] = KS,
    dim: int = 8,
) -> tuple[np.ndarray, ...]:
    X = np.asarray(features.X, dtype=float)
    if X.ndim != 2 or len(X) < 20:
        raise ValueError("phase validation requires at least 20 feature epochs")
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


def _onset_epoch_indices(onsets_s: np.ndarray, epoch_s: float, n_epochs: int) -> np.ndarray:
    onsets = np.asarray(onsets_s, dtype=float)
    if epoch_s <= 0 or n_epochs < 2:
        raise ValueError("epoch grid is invalid")
    if onsets.ndim != 1 or onsets.size < 3 or np.any(~np.isfinite(onsets)):
        raise ValueError("at least three finite onsets are required")
    idx = np.rint(onsets / float(epoch_s)).astype(int)
    if np.any(idx < 0) or np.any(idx >= int(n_epochs)):
        raise ValueError("T0 onset falls outside the feature timeline")
    if np.any(np.diff(idx) <= 0):
        raise ValueError("T0 onsets collapse or reverse on the feature epoch grid")
    return idx


def _phase_score_from_indices(label_sets: Sequence[np.ndarray], indices: np.ndarray) -> float:
    if not label_sets:
        raise ValueError("at least one state labelling is required")
    idx = np.asarray(indices, dtype=int)
    if idx.ndim != 1 or idx.size < 3:
        raise ValueError("at least three event indices are required")
    n_epochs = len(np.asarray(label_sets[0]))
    if any(len(np.asarray(labels)) != n_epochs for labels in label_sets):
        raise ValueError("state labellings must share one timeline")
    if np.any(idx < 0) or np.any(idx >= n_epochs):
        raise ValueError("event index outside state timeline")
    scores = [
        float(
            np.mean(
                np.asarray(labels, dtype=int)[idx[:-1]]
                == np.asarray(labels, dtype=int)[idx[1:]]
            )
        )
        for labels in label_sets
    ]
    return float(np.mean(scores))


def phase_locked_state_recurrence(
    label_sets: Sequence[np.ndarray],
    event_onsets_s: np.ndarray,
    epoch_s: float,
) -> float:
    labels0 = np.asarray(label_sets[0]) if label_sets else np.asarray([])
    indices = _onset_epoch_indices(event_onsets_s, epoch_s, len(labels0))
    return _phase_score_from_indices(label_sets, indices)


def evaluate_run_phase_alignment(
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
    n_epochs = len(label_sets[0])
    t0 = _t0_onsets(events)
    indices = _onset_epoch_indices(t0, features.epoch_s, n_epochs)
    score = _phase_score_from_indices(label_sets, indices)

    rng = np.random.default_rng(seed)
    offsets = rng.choice(
        np.arange(1, n_epochs, dtype=int),
        size=n_null,
        replace=n_null > (n_epochs - 1),
    )
    null_scores = np.asarray(
        [
            _phase_score_from_indices(label_sets, (indices + int(offset)) % n_epochs)
            for offset in offsets
        ],
        dtype=float,
    )
    p_value = (1 + int(np.sum(null_scores >= score))) / (1 + n_null)
    return ClockValidationResult(
        subject=int(subject),
        run=int(run),
        score=float(score),
        null_scores=null_scores,
        p_value=float(p_value),
        positive_direction=bool(score > np.median(null_scores)),
    )


def run_gate1b(
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
        "null": NULL_NAME,
        "event_sampling": "nearest_feature_epoch",
    }
    fingerprint = config_fingerprint(config)
    output_path = None if output is None else Path(output)
    records: list[dict[str, object]] = []
    done: set[tuple[int, int]] = set()
    if resume and output_path is not None and output_path.exists():
        prior = json.loads(output_path.read_text(encoding="utf-8"))
        if prior.get("config_fingerprint") != fingerprint:
            raise ValueError("resume receipt config does not match current Gate 1B config")
        records = list(prior.get("runs", []))
        done = {
            (int(item["subject"]), int(item["run"]))
            for item in records
            if item.get("status") == "OK"
        }

    for run in runs:
        if (run.subject, run.run) in done:
            continue
        try:
            features, events = load_run(run)
            result = evaluate_run_phase_alignment(
                features,
                events,
                run.subject,
                run.run,
                n_null=n_null,
                seed=seed + 1000 * run.subject + run.run,
            )
            record = {
                "status": "OK",
                **asdict(result),
                "artifact_stats": None
                if features.artifact_stats is None
                else asdict(features.artifact_stats),
            }
        except (MissingAnnotationsError, MalformedAnnotationsError, ValueError) as exc:
            record = {
                "status": "SKIP",
                "subject": run.subject,
                "run": run.run,
                "reason": str(exc),
            }
        records.append(record)
        if output_path is not None:
            write_receipt(
                output_path,
                {
                    "gate": "gate1b_eegmmidb_phase_alignment",
                    "status": "IN_PROGRESS",
                    "null": NULL_NAME,
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
        aggregate_p = float(
            (1 + int(np.sum(aggregate_null >= real_median)))
            / (1 + len(aggregate_null))
        )
        positive_fraction = float(
            np.mean([bool(item["positive_direction"]) for item in heldout_results])
        )
        status = "PASS" if aggregate_p <= 0.05 and positive_fraction >= 2 / 3 else "FAIL"

    receipt: dict[str, object] = {
        "gate": "gate1b_eegmmidb_phase_alignment",
        "status": status,
        "null": NULL_NAME,
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
    parser = argparse.ArgumentParser(
        description="Validate EEGMMIDB phase-locked state recurrence against circular clock shifts"
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subjects", type=int, nargs="*")
    parser.add_argument("--n-null", type=int, default=99)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    receipt = run_gate1b(
        args.data,
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
