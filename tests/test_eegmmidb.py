from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from brainloops.datasets.eegmmidb import (
    MalformedAnnotationsError,
    MissingAnnotationsError,
    discover_runs,
    load_run,
    parse_t_annotations,
)


def test_discover_runs_sorts_subject_and_run_and_skips_unrelated(tmp_path):
    (tmp_path / "S002").mkdir()
    (tmp_path / "S001").mkdir()
    (tmp_path / "S002" / "S002R03.edf").touch()
    (tmp_path / "S001" / "S001R14.edf").touch()
    (tmp_path / "S001" / "S001R03.edf").touch()
    (tmp_path / "S001" / "notes.edf").touch()
    (tmp_path / "S001" / "S001R03.txt").touch()

    runs = discover_runs(tmp_path)
    assert [(r.subject, r.run, r.path.name) for r in runs] == [
        (1, 3, "S001R03.edf"),
        (1, 14, "S001R14.edf"),
        (2, 3, "S002R03.edf"),
    ]
    assert [(r.subject, r.run) for r in discover_runs(tmp_path, subjects=[2])] == [(2, 3)]


def _raw(onsets, descriptions):
    return SimpleNamespace(
        annotations=SimpleNamespace(
            onset=np.asarray(onsets, dtype=float),
            description=np.asarray(descriptions, dtype=object),
        )
    )


def test_parse_t_annotations_preserves_exact_labels_and_ignores_documented_unknowns():
    events = parse_t_annotations(_raw([0, 1, 4, 8], ["BAD", "T0", "T1", "T2"]))
    assert [(e.onset_s, e.label) for e in events.events] == [(1.0, "T0"), (4.0, "T1"), (8.0, "T2")]


def test_parse_t_annotations_requires_all_three_task_codes():
    with pytest.raises(MissingAnnotationsError):
        parse_t_annotations(_raw([0, 4], ["T0", "T1"]))


def test_parse_t_annotations_rejects_non_increasing_event_order():
    with pytest.raises(MalformedAnnotationsError):
        parse_t_annotations(_raw([0, 8, 4], ["T0", "T1", "T2"]))


@pytest.mark.skipif("EEGMMIDB_ROOT" not in os.environ, reason="EEGMMIDB_ROOT not set")
def test_real_eegmmidb_smoke():
    root = Path(os.environ["EEGMMIDB_ROOT"])
    task_runs = [run for run in discover_runs(root) if run.run >= 3]
    if not task_runs:
        pytest.skip("no task EDF files found")
    features, events = load_run(task_runs[0])
    assert np.all(np.isfinite(features.X))
    assert features.X.shape[0] >= 2
    assert len(events.events) > 0
