from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import numpy as np

from brainloops.types import Event, EventSeries, FeatureBatch


def _gate1c():
    spec = importlib.util.find_spec("experiments.gate1c_eegmmidb")
    assert spec is not None, "Gate 1C experiment module is missing"
    module = importlib.import_module("experiments.gate1c_eegmmidb")
    for name in (
        "evaluate_run_transition_geometry",
        "history_conditioned_similarity",
        "run_gate1c",
        "transition_consistency_score",
    ):
        assert hasattr(module, name), f"Gate 1C is missing {name}"
    return module


def _events_from_t0_indices(indices: np.ndarray, epoch_s: float = 0.5) -> EventSeries:
    events: list[Event] = []
    for j, idx in enumerate(indices):
        events.append(Event(float(idx * epoch_s), "T0"))
        if j + 1 < len(indices):
            mid = (int(idx) + int(indices[j + 1])) // 2
            events.append(Event(float(mid * epoch_s), "T1" if j % 2 == 0 else "T2"))
    events.sort(key=lambda event: event.onset_s)
    return EventSeries(events=tuple(events))


def _anchored_batch(seed: int = 7) -> tuple[FeatureBatch, EventSeries]:
    rng = np.random.default_rng(seed)
    n_epochs = 482
    t0_idx = np.array([
        4, 20, 37, 53, 70, 86, 103, 119, 136, 152, 169, 185, 202, 218, 235,
        251, 268, 284, 301, 317, 334, 350, 367, 383, 400, 416, 433, 449, 466,
    ])
    X = 0.15 * rng.standard_normal((n_epochs, 4))
    before = np.array([-4.0, 3.0, -2.0, 1.0])
    after = -before
    for idx in t0_idx:
        X[idx - 1] += before
        X[idx + 1] += after
    batch = FeatureBatch(X=X, epoch_s=0.5, feature_names=("a", "b", "c", "d"))
    return batch, _events_from_t0_indices(t0_idx)


def test_transition_consistency_score_is_high_for_repeated_direction():
    gate1c = _gate1c()
    Z = np.zeros((40, 2), dtype=float)
    idx = np.array([5, 12, 19, 26, 33])
    for i in idx:
        Z[i - 1] = np.array([-1.0, 0.0])
        Z[i + 1] = np.array([1.0, 0.0])
    score = gate1c.transition_consistency_score(Z, idx, half_window=1)
    assert score > 0.99


def test_event_locked_transition_direction_beats_circular_shift_null():
    gate1c = _gate1c()
    features, events = _anchored_batch()
    result = gate1c.evaluate_run_transition_geometry(
        features,
        events,
        subject=1,
        run=3,
        n_null=99,
        seed=11,
        half_window=1,
    )
    assert result.p_value <= 0.05
    assert result.positive_direction
    assert result.score > np.median(result.null_scores)
    assert result.n_events >= 20


def test_period_only_cycle_does_not_pass_transition_geometry_gate():
    gate1c = _gate1c()
    rng = np.random.default_rng(9)
    n_epochs = 482
    phase = 2 * np.pi * np.arange(n_epochs) / 16.0
    X = np.c_[
        np.cos(phase),
        np.sin(phase),
        np.cos(phase + 0.7),
        np.sin(phase + 1.1),
    ] + 1e-8 * rng.standard_normal((n_epochs, 4))
    regular_t0 = np.arange(4, 469, 16)
    result = gate1c.evaluate_run_transition_geometry(
        FeatureBatch(X=X, epoch_s=0.5, feature_names=("a", "b", "c", "d")),
        _events_from_t0_indices(regular_t0),
        subject=1,
        run=3,
        n_null=99,
        seed=13,
        half_window=1,
    )
    assert not (result.p_value <= 0.05 and result.positive_direction)


def test_history_diagnostic_separates_same_from_different_preceding_tasks():
    gate1c = _gate1c()
    vectors = np.array([
        [1.0, 0.0],
        [0.95, 0.05],
        [-1.0, 0.0],
        [-0.95, 0.05],
    ])
    diagnostic = gate1c.history_conditioned_similarity(vectors, ("T1", "T1", "T2", "T2"))
    assert diagnostic["same_history_cosine"] > 0.99
    assert diagnostic["different_history_cosine"] < -0.99
    assert diagnostic["history_delta"] > 1.9


def test_gate1c_runner_aggregates_and_resumes(monkeypatch, tmp_path):
    gate1c = _gate1c()
    from brainloops.types import EEGMMIDBRun

    runs = [EEGMMIDBRun(subject=s, run=3, path=Path(f"S{s:03d}R03.edf")) for s in (1, 2, 3)]
    monkeypatch.setattr(gate1c, "discover_runs", lambda root, subjects=None: runs)

    def fake_load(run):
        return _anchored_batch(seed=100 + run.subject)

    monkeypatch.setattr(gate1c, "load_run", fake_load)
    output = tmp_path / "gate1c.json"
    receipt = gate1c.run_gate1c(
        "/synthetic",
        subjects=[1, 2, 3],
        n_null=39,
        output=output,
        seed=17,
        half_window=1,
    )
    assert receipt["status"] == "PASS"
    assert receipt["gate"] == "gate1c_eegmmidb_transition_geometry"
    assert receipt["null"] == "circular_annotation_shift_fixed_transition_timeline"
    assert receipt["analysis_scope"] == "post_gate1b_followup_same_dataset"
    assert output.exists()

    monkeypatch.setattr(
        gate1c,
        "load_run",
        lambda run: (_ for _ in ()).throw(AssertionError("resume reloaded completed run")),
    )
    resumed = gate1c.run_gate1c(
        "/synthetic",
        subjects=[1, 2, 3],
        n_null=39,
        output=output,
        resume=True,
        seed=17,
        half_window=1,
    )
    assert resumed["status"] == "PASS"


def test_gate1c_script_runs_from_source_tree():
    gate1c = _gate1c()
    assert gate1c is not None
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "experiments/gate1c_eegmmidb.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
