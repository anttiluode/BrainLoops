from __future__ import annotations

from pathlib import Path

import numpy as np

from brainloops.types import Event, EventSeries, FeatureBatch
from experiments.gate1b_eegmmidb import (
    evaluate_run_phase_alignment,
    phase_locked_state_recurrence,
    run_gate1b,
)


def _events_from_t0_indices(indices: np.ndarray, epoch_s: float = 0.5) -> EventSeries:
    events: list[Event] = []
    for j, idx in enumerate(indices):
        events.append(Event(float(idx * epoch_s), "T0"))
        if j + 1 < len(indices):
            mid = (int(idx) + int(indices[j + 1])) // 2
            events.append(Event(float(mid * epoch_s), "T1" if j % 2 == 0 else "T2"))
    events.sort(key=lambda event: event.onset_s)
    return EventSeries(events=tuple(events))


def test_phase_locked_score_uses_absolute_t0_phase_not_just_period():
    rng = np.random.default_rng(3)
    labels = rng.integers(0, 6, size=240)
    t0_idx = np.array([4, 21, 37, 54, 70, 87, 103, 120, 136, 153, 169, 186, 202, 219])
    labels[t0_idx] = 5
    real = phase_locked_state_recurrence((labels,), t0_idx * 0.5, epoch_s=0.5)
    shifted = phase_locked_state_recurrence((labels,), ((t0_idx + 3) % len(labels)) * 0.5, epoch_s=0.5)
    assert real == 1.0
    assert shifted < 0.5


def test_phase_alignment_passes_event_locked_anchor_but_not_period_only_control():
    rng = np.random.default_rng(7)
    n_epochs = 480
    t0_idx = np.array([
        4, 20, 37, 53, 70, 86, 103, 119, 136, 152, 169, 185, 202, 218, 235,
        251, 268, 284, 301, 317, 334, 350, 367, 383, 400, 416, 433, 449, 466,
    ])

    X_anchor = rng.standard_normal((n_epochs, 4))
    X_anchor[t0_idx] = np.array([12.0, -12.0, 8.0, -8.0])
    anchored = evaluate_run_phase_alignment(
        FeatureBatch(X=X_anchor, epoch_s=0.5, feature_names=("a", "b", "c", "d")),
        _events_from_t0_indices(t0_idx),
        subject=1,
        run=3,
        n_null=99,
        seed=11,
    )
    assert anchored.p_value <= 0.05
    assert anchored.positive_direction

    phase = 2 * np.pi * np.arange(n_epochs) / 16.0
    X_periodic = np.c_[
        np.cos(phase),
        np.sin(phase),
        np.cos(phase + 0.7),
        np.sin(phase + 1.1),
    ] + 1e-6 * rng.standard_normal((n_epochs, 4))
    regular_t0 = np.arange(4, 468, 16)
    periodic = evaluate_run_phase_alignment(
        FeatureBatch(X=X_periodic, epoch_s=0.5, feature_names=("a", "b", "c", "d")),
        _events_from_t0_indices(regular_t0),
        subject=1,
        run=3,
        n_null=99,
        seed=11,
    )
    assert not (periodic.p_value <= 0.05 and periodic.positive_direction)


def test_gate1b_runner_aggregates_heldout_subjects_and_is_resumable(monkeypatch, tmp_path):
    import experiments.gate1b_eegmmidb as gate1b
    from brainloops.types import EEGMMIDBRun

    rng = np.random.default_rng(13)
    n_epochs = 480
    t0_idx = np.array([
        4, 20, 37, 53, 70, 86, 103, 119, 136, 152, 169, 185, 202, 218, 235,
        251, 268, 284, 301, 317, 334, 350, 367, 383, 400, 416, 433, 449, 466,
    ])
    events = _events_from_t0_indices(t0_idx)

    def fake_load(run):
        X = rng.standard_normal((n_epochs, 4))
        X[t0_idx] = np.array([12.0, -12.0, 8.0, -8.0])
        return FeatureBatch(X=X, epoch_s=0.5, feature_names=("a", "b", "c", "d")), events

    runs = [EEGMMIDBRun(subject=s, run=3, path=Path(f"S{s:03d}R03.edf")) for s in (1, 2, 3)]
    monkeypatch.setattr(gate1b, "discover_runs", lambda root, subjects=None: runs)
    monkeypatch.setattr(gate1b, "load_run", fake_load)
    output = tmp_path / "gate1b.json"
    receipt = run_gate1b("/synthetic", subjects=[1, 2, 3], n_null=39, output=output, seed=17)
    assert receipt["status"] == "PASS"
    assert receipt["gate"] == "gate1b_eegmmidb_phase_alignment"
    assert receipt["null"] == "circular_annotation_shift_fixed_state_timeline"
    assert output.exists()

    monkeypatch.setattr(
        gate1b,
        "load_run",
        lambda run: (_ for _ in ()).throw(AssertionError("resume reloaded completed run")),
    )
    resumed = run_gate1b("/synthetic", subjects=[1, 2, 3], n_null=39, output=output, resume=True, seed=17)
    assert resumed["status"] == "PASS"


def test_gate1b_script_runs_from_source_tree():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "experiments/gate1b_eegmmidb.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
