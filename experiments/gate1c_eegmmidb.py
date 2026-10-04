from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
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
from brainloops.types import EventSeries, FeatureBatch

NULL_NAME = "circular_annotation_shift_fixed_transition_timeline"
ANALYSIS_SCOPE = "post_gate1b_followup_same_dataset"
PCA_DIM = 8
TIE_ATOL = 1e-12


@dataclass(frozen=True)
class TransitionGeometryResult:
    subject: int
    run: int
    score: float
    null_scores: np.ndarray
    p_value: float
    positive_direction: bool
    n_events: int
    history_same_cosine: float | None
    history_different_cosine: float | None
    history_delta: float | None


def deterministic_subject_split(subjects: Sequence[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    unique = tuple(sorted({int(subject) for subject in subjects}))
    development = tuple(subject for subject in unique if subject % 5 == 0)
    heldout = tuple(subject for subject in unique if subject % 5 != 0)
    return development, heldout


def _t0_onsets_and_preceding_tasks(events: EventSeries) -> tuple[np.ndarray, tuple[str | None, ...]]:
    onsets: list[float] = []
    preceding: list[str | None] = []
    last_task: str | None = None
    for event in events.events:
        if event.label in {"T1", "T2"}:
            last_task = event.label
        elif event.label == "T0":
            onsets.append(float(event.onset_s))
            preceding.append(last_task)
    values = np.asarray(onsets, dtype=float)
    if values.size < 3:
        raise MissingAnnotationsError("at least three T0 onsets are required for transition validation")
    if np.any(~np.isfinite(values)) or np.any(np.diff(values) <= 0):
        raise MalformedAnnotationsError("T0 onsets must be finite and strictly increasing")
    return values, tuple(preceding)


def _pca_trajectory(features: FeatureBatch, dim: int = PCA_DIM) -> np.ndarray:
    X = np.asarray(features.X, dtype=float)
    if X.ndim != 2 or len(X) < 20:
        raise ValueError("transition validation requires at least 20 feature epochs")
    if np.any(~np.isfinite(X)):
        raise ValueError("transition validation requires finite features")
    n_dim = min(int(dim), X.shape[1], X.shape[0] - 1)
    if n_dim < 1:
        raise ValueError("no PCA dimensions available")
    return PCA(n_components=n_dim).fit_transform(X)


def _onset_epoch_indices(onsets_s: np.ndarray, epoch_s: float, n_epochs: int) -> np.ndarray:
    onsets = np.asarray(onsets_s, dtype=float)
    if epoch_s <= 0 or n_epochs < 3:
        raise ValueError("epoch grid is invalid")
    if onsets.ndim != 1 or onsets.size < 3 or np.any(~np.isfinite(onsets)):
        raise ValueError("at least three finite onsets are required")
    idx = np.rint(onsets / float(epoch_s)).astype(int)
    if np.any(idx < 0) or np.any(idx >= int(n_epochs)):
        raise ValueError("T0 onset falls outside the feature timeline")
    if np.any(np.diff(idx) <= 0):
        raise ValueError("T0 onsets collapse or reverse on the feature epoch grid")
    return idx


def _transition_vectors_raw(trajectory: np.ndarray, indices: np.ndarray, half_window: int) -> np.ndarray:
    Z = np.asarray(trajectory, dtype=float)
    idx = np.asarray(indices, dtype=int)
    width = int(half_window)
    if Z.ndim != 2 or len(Z) < 3:
        raise ValueError("trajectory must be a two-dimensional epoch-by-state array")
    if width < 1:
        raise ValueError("half_window must be at least one epoch")
    if idx.ndim != 1 or idx.size < 3:
        raise ValueError("at least three event indices are required")
    if np.any(idx < width) or np.any(idx + width >= len(Z)):
        raise ValueError("event transition window falls outside trajectory")
    vectors = []
    for center in idx:
        pre = np.mean(Z[center - width : center], axis=0)
        post = np.mean(Z[center + 1 : center + width + 1], axis=0)
        vectors.append(post - pre)
    return np.asarray(vectors, dtype=float)


def _score_vectors(vectors: np.ndarray) -> float:
    V = np.asarray(vectors, dtype=float)
    if V.ndim != 2 or len(V) < 3:
        raise ValueError("at least three transition vectors are required")
    norms = np.linalg.norm(V, axis=1)
    keep = np.isfinite(norms) & (norms > 1e-12) & np.all(np.isfinite(V), axis=1)
    V = V[keep]
    norms = norms[keep]
    if len(V) < 3:
        raise ValueError("at least three nonzero finite transition vectors are required")
    unit = V / norms[:, None]
    similarities = unit @ unit.T
    n = len(unit)
    return float((np.sum(similarities) - n) / (n * (n - 1)))


def transition_consistency_score(
    trajectory: np.ndarray,
    indices: np.ndarray,
    half_window: int = 1,
) -> float:
    """Mean off-diagonal cosine similarity of symmetric pre/post transition vectors."""
    vectors = _transition_vectors_raw(trajectory, indices, int(half_window))
    return _score_vectors(vectors)


def history_conditioned_similarity(
    vectors: np.ndarray,
    preceding_labels: Sequence[str | None],
) -> dict[str, float | None]:
    """Secondary diagnostic: transition similarity for same vs different preceding task labels."""
    V = np.asarray(vectors, dtype=float)
    labels = tuple(preceding_labels)
    if V.ndim != 2 or len(V) != len(labels):
        raise ValueError("vectors and preceding labels must share one event axis")
    norms = np.linalg.norm(V, axis=1)
    keep = np.isfinite(norms) & (norms > 1e-12) & np.all(np.isfinite(V), axis=1)
    keep &= np.asarray([label in {"T1", "T2"} for label in labels], dtype=bool)
    V = V[keep]
    kept_labels = [label for label, use in zip(labels, keep) if use]
    if len(V) < 2:
        return {
            "same_history_cosine": None,
            "different_history_cosine": None,
            "history_delta": None,
        }
    unit = V / np.linalg.norm(V, axis=1)[:, None]
    same: list[float] = []
    different: list[float] = []
    for i in range(len(unit)):
        for j in range(i + 1, len(unit)):
            value = float(np.dot(unit[i], unit[j]))
            if kept_labels[i] == kept_labels[j]:
                same.append(value)
            else:
                different.append(value)
    same_mean = None if not same else float(np.mean(same))
    different_mean = None if not different else float(np.mean(different))
    delta = None if same_mean is None or different_mean is None else float(same_mean - different_mean)
    return {
        "same_history_cosine": same_mean,
        "different_history_cosine": different_mean,
        "history_delta": delta,
    }


def _permutation_p(null_scores: np.ndarray, score: float) -> float:
    values = np.asarray(null_scores, dtype=float)
    return float((1 + int(np.sum(values >= float(score) - TIE_ATOL))) / (1 + len(values)))


def evaluate_run_transition_geometry(
    features: FeatureBatch,
    events: EventSeries,
    subject: int,
    run: int,
    n_null: int = 99,
    seed: int = 0,
    half_window: int = 1,
) -> TransitionGeometryResult:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    width = int(half_window)
    if width < 1:
        raise ValueError("half_window must be at least one epoch")

    Z = _pca_trajectory(features)
    onsets, preceding = _t0_onsets_and_preceding_tasks(events)
    indices = _onset_epoch_indices(onsets, features.epoch_s, len(Z))
    valid = (indices >= width) & (indices + width < len(Z))
    indices = indices[valid]
    preceding_valid = tuple(label for label, use in zip(preceding, valid) if use)
    if len(indices) < 3:
        raise ValueError("fewer than three T0 transitions have a complete symmetric window")

    vectors = _transition_vectors_raw(Z, indices, width)
    norms = np.linalg.norm(vectors, axis=1)
    finite_nonzero = np.isfinite(norms) & (norms > 1e-12) & np.all(np.isfinite(vectors), axis=1)
    vectors = vectors[finite_nonzero]
    indices = indices[finite_nonzero]
    preceding_valid = tuple(label for label, use in zip(preceding_valid, finite_nonzero) if use)
    if len(indices) < 3:
        raise ValueError("fewer than three nonzero T0 transition vectors remain")

    score = _score_vectors(vectors)
    ring_length = len(Z) - 2 * width
    if ring_length <= 1:
        raise ValueError("trajectory is too short for circular phase shifts")
    rng = np.random.default_rng(seed)
    possible_offsets = np.arange(1, ring_length, dtype=int)
    offsets = rng.choice(
        possible_offsets,
        size=n_null,
        replace=n_null > len(possible_offsets),
    )
    base = indices - width
    null_values: list[float] = []
    for offset in offsets:
        shifted = width + ((base + int(offset)) % ring_length)
        null_values.append(transition_consistency_score(Z, shifted, width))
    null_scores = np.asarray(null_values, dtype=float)
    p_value = _permutation_p(null_scores, score)
    diagnostic = history_conditioned_similarity(vectors, preceding_valid)
    return TransitionGeometryResult(
        subject=int(subject),
        run=int(run),
        score=float(score),
        null_scores=null_scores,
        p_value=p_value,
        positive_direction=bool(score > np.median(null_scores) + TIE_ATOL),
        n_events=int(len(indices)),
        history_same_cosine=diagnostic["same_history_cosine"],
        history_different_cosine=diagnostic["different_history_cosine"],
        history_delta=diagnostic["history_delta"],
    )


def run_gate1c(
    data: str | Path,
    subjects: Sequence[int] | None = None,
    n_null: int = 99,
    output: str | Path | None = None,
    resume: bool = False,
    seed: int = 0,
    half_window: int = 1,
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
        "pca_dim": PCA_DIM,
        "half_window_epochs": int(half_window),
        "metric": "mean_pairwise_cosine_symmetric_pca_transition_vectors",
        "null": NULL_NAME,
        "event_sampling": "nearest_feature_epoch",
        "analysis_scope": ANALYSIS_SCOPE,
    }
    fingerprint = config_fingerprint(config)
    output_path = None if output is None else Path(output)
    records: list[dict[str, object]] = []
    done: set[tuple[int, int]] = set()
    if resume and output_path is not None and output_path.exists():
        prior = json.loads(output_path.read_text(encoding="utf-8"))
        if prior.get("config_fingerprint") != fingerprint:
            raise ValueError("resume receipt config does not match current Gate 1C config")
        records = list(prior.get("runs", []))
        done = {
            (int(item["subject"]), int(item["run"]))
            for item in records
            if item.get("status") == "OK"
        }

    for item in runs:
        if (item.subject, item.run) in done:
            continue
        try:
            features, events = load_run(item)
            result = evaluate_run_transition_geometry(
                features,
                events,
                item.subject,
                item.run,
                n_null=n_null,
                seed=seed + 1000 * item.subject + item.run,
                half_window=half_window,
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
                "subject": item.subject,
                "run": item.run,
                "reason": str(exc),
            }
        records.append(record)
        if output_path is not None:
            write_receipt(
                output_path,
                {
                    "gate": "gate1c_eegmmidb_transition_geometry",
                    "status": "IN_PROGRESS",
                    "analysis_scope": ANALYSIS_SCOPE,
                    "null": NULL_NAME,
                    "config": config,
                    "config_fingerprint": fingerprint,
                    "development_subjects": development,
                    "heldout_subjects": heldout,
                    "runs": records,
                },
            )

    successful = [record for record in records if record.get("status") == "OK"]
    subject_results: list[dict[str, object]] = []
    for subject in subject_ids:
        items = [record for record in successful if int(record["subject"]) == subject]
        if not items:
            continue
        score = float(np.median([float(record["score"]) for record in items]))
        null_matrix = np.asarray([record["null_scores"] for record in items], dtype=float)
        null_scores = np.median(null_matrix, axis=0)
        p_value = _permutation_p(null_scores, score)
        history_values = [
            float(record["history_delta"])
            for record in items
            if record.get("history_delta") is not None
        ]
        subject_results.append(
            {
                "subject": subject,
                "score": score,
                "null_scores": null_scores,
                "p_value": p_value,
                "positive_direction": bool(score > np.median(null_scores) + TIE_ATOL),
                "n_runs": len(items),
                "history_delta_median": None
                if not history_values
                else float(np.median(history_values)),
            }
        )

    heldout_results = [item for item in subject_results if int(item["subject"]) in heldout]
    if n_null < 19 or len(heldout_results) < 3:
        status = "INSUFFICIENT_DATA"
        aggregate_p = None
        positive_fraction = None
        aggregate_history_delta = None
    else:
        real_median = float(np.median([float(item["score"]) for item in heldout_results]))
        null_matrix = np.asarray([item["null_scores"] for item in heldout_results], dtype=float)
        aggregate_null = np.median(null_matrix, axis=0)
        aggregate_p = _permutation_p(aggregate_null, real_median)
        positive_fraction = float(
            np.mean([bool(item["positive_direction"]) for item in heldout_results])
        )
        history_values = [
            float(item["history_delta_median"])
            for item in heldout_results
            if item.get("history_delta_median") is not None
        ]
        aggregate_history_delta = None if not history_values else float(np.median(history_values))
        status = "PASS" if aggregate_p <= 0.05 and positive_fraction >= 2 / 3 else "FAIL"

    receipt: dict[str, object] = {
        "gate": "gate1c_eegmmidb_transition_geometry",
        "status": status,
        "analysis_scope": ANALYSIS_SCOPE,
        "null": NULL_NAME,
        "config": config,
        "config_fingerprint": fingerprint,
        "development_subjects": development,
        "heldout_subjects": heldout,
        "runs": records,
        "subjects": subject_results,
        "aggregate_p": aggregate_p,
        "positive_fraction": positive_fraction,
        "aggregate_history_delta": aggregate_history_delta,
        "history_diagnostic_is_primary": False,
    }
    if output_path is not None:
        write_receipt(output_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test repeated EEGMMIDB T0 transition geometry against circular clock shifts"
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subjects", type=int, nargs="*")
    parser.add_argument("--n-null", type=int, default=99)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--half-window", type=int, default=1)
    args = parser.parse_args()
    receipt = run_gate1c(
        args.data,
        subjects=args.subjects,
        n_null=args.n_null,
        output=args.output,
        resume=args.resume,
        seed=args.seed,
        half_window=args.half_window,
    )
    print(receipt["status"])
    return 0 if receipt["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
