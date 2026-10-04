from __future__ import annotations

from pathlib import Path

import numpy as np

from brainloops.types import Event, EventSeries, FeatureBatch
from experiments.gate1_eegmmidb import (
    clock_alignment_score,
    deterministic_subject_split,
    evaluate_run_clock,
)


def _periodic_feature_batch(seed: int = 0, shuffle: bool = False) -> FeatureBatch:
    rng = np.random.default_rng(seed)
    n_epochs = 480
    cycle_epochs = 16  # 8 s at 0.5 s/epoch
    phase = 2 * np.pi * np.arange(n_epochs) / cycle_epochs
    X = np.c_[
        np.cos(phase),
        np.sin(phase),
        np.cos(phase + 0.7),
        np.sin(phase + 1.1),
    ] + 0.04 * rng.standard_normal((n_epochs, 4))
    if shuffle:
        X = X[rng.permutation(n_epochs)]
    return FeatureBatch(X=X, epoch_s=0.5, feature_names=("a", "b", "c", "d"))


def _clock_events() -> EventSeries:
    # T0 repeats every full 8 s rest/task cycle. T1/T2 are deliberately
    # present but are not needed by the period score itself.
    events = []
    for i, onset in enumerate(np.arange(0.0, 240.0, 4.0)):
        label = "T0" if i % 2 == 0 else ("T1" if (i // 2) % 2 == 0 else "T2")
        events.append(Event(float(onset), label))
    return EventSeries(events=tuple(events))


def test_clock_alignment_score_rewards_recurrence_mass_at_t0_cycle():
    periods = np.array([7.8, 8.0, 8.2, 3.0, 13.0])
    weights = np.array([4.0, 6.0, 4.0, 1.0, 1.0])
    t0 = np.arange(0.0, 80.0, 8.0)
    aligned = clock_alignment_score(periods, weights, t0)
    off = clock_alignment_score(periods + 3.0, weights, t0)
    assert aligned > 0.7
    assert aligned > off


def test_planted_clock_passes_posthoc_alignment_but_time_randomized_control_does_not():
    events = _clock_events()
    planted = evaluate_run_clock(_periodic_feature_batch(1), events, subject=1, run=3, n_null=39, seed=5)
    randomized = evaluate_run_clock(_periodic_feature_batch(1, shuffle=True), events, subject=1, run=3, n_null=39, seed=5)
    assert planted.p_value <= 0.05
    assert planted.positive_direction
    assert planted.score > randomized.score
    assert not (randomized.p_value <= 0.05 and randomized.positive_direction)


def test_subject_split_is_deterministic_from_subject_id():
    development, heldout = deterministic_subject_split([7, 5, 2, 10, 1])
    assert development == (5, 10)
    assert heldout == (1, 2, 7)
    assert set(development).isdisjoint(heldout)


def test_gate1_runner_is_resumable_and_passes_planted_clock(monkeypatch, tmp_path):
    import experiments.gate1_eegmmidb as gate1
    from brainloops.types import EEGMMIDBRun

    runs = [EEGMMIDBRun(subject=s, run=3, path=Path(f"S{s:03d}R03.edf")) for s in (1, 2, 3)]
    monkeypatch.setattr(gate1, "discover_runs", lambda root, subjects=None: runs)
    monkeypatch.setattr(
        gate1,
        "load_run",
        lambda run: (_periodic_feature_batch(run.subject), _clock_events()),
    )
    output = tmp_path / "gate1.json"
    receipt = gate1.run_gate1("/synthetic", subjects=[1, 2, 3], n_null=39, output=output, seed=9)
    assert receipt["status"] == "PASS"
    assert receipt["config"]["code_version"] == "0.1.0"
    assert receipt["config"]["n_null"] == 39
    assert receipt["heldout_subjects"] == (1, 2, 3)
    assert output.exists()

    monkeypatch.setattr(gate1, "load_run", lambda run: (_ for _ in ()).throw(AssertionError("resume reloaded a completed run")))
    resumed = gate1.run_gate1("/synthetic", subjects=[1, 2, 3], n_null=39, output=output, resume=True, seed=9)
    assert resumed["status"] == "PASS"


def test_gate1_reports_insufficient_data_for_two_heldout_subjects(monkeypatch):
    import experiments.gate1_eegmmidb as gate1
    from brainloops.types import EEGMMIDBRun

    runs = [EEGMMIDBRun(subject=s, run=3, path=Path(f"S{s:03d}R03.edf")) for s in (1, 2)]
    monkeypatch.setattr(gate1, "discover_runs", lambda root, subjects=None: runs)
    monkeypatch.setattr(gate1, "load_run", lambda run: (_periodic_feature_batch(run.subject), _clock_events()))
    receipt = gate1.run_gate1("/synthetic", subjects=[1, 2], n_null=39, seed=4)
    assert receipt["status"] == "INSUFFICIENT_DATA"


def test_gate1_script_runs_from_source_tree():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "experiments/gate1_eegmmidb.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
