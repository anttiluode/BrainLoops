from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from brainloops.datasets.lemon import (
    LemonRecording,
    discover_recordings,
    normalize_rest_marker,
    parse_rest_blocks,
    feature_blocks_from_raw,
)


def _write_brainvision_stub(root: Path, subject: str, duplicate: bool = False, missing_marker: bool = False):
    d = root / subject / "RSEEG"
    d.mkdir(parents=True, exist_ok=True)
    stem = f"{subject}.vhdr" if not duplicate else f"{subject}-copy.vhdr"
    vhdr = d / stem
    eeg_name = stem.replace(".vhdr", ".eeg")
    vmrk_name = stem.replace(".vhdr", ".vmrk")
    vhdr.write_text(f"Brain Vision Data Exchange Header File Version 1.0\n[Common Infos]\nDataFile={eeg_name}\nMarkerFile={vmrk_name}\n", encoding="utf-8")
    (d / eeg_name).touch()
    if not missing_marker:
        (d / vmrk_name).touch()
    return vhdr


def test_discover_recordings_preserves_literal_subject_and_requires_unique_complete_triplet(tmp_path):
    _write_brainvision_stub(tmp_path, "sub-010002")
    _write_brainvision_stub(tmp_path, "sub-010003")
    found = discover_recordings(tmp_path)
    assert [(x.subject_id, x.path.name) for x in found] == [
        ("sub-010002", "sub-010002.vhdr"),
        ("sub-010003", "sub-010003.vhdr"),
    ]
    assert all(x.marker_path.exists() and x.data_path.exists() for x in found)

    _write_brainvision_stub(tmp_path, "sub-010002", duplicate=True)
    with pytest.raises(ValueError, match="multiple"):
        discover_recordings(tmp_path)


def test_discover_recordings_rejects_missing_companion(tmp_path):
    _write_brainvision_stub(tmp_path, "sub-010004", missing_marker=True)
    with pytest.raises(ValueError, match="companion"):
        discover_recordings(tmp_path)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("S200", "EO"), ("S 200", "EO"), ("Stimulus/S200", "EO"),
        ("Stimulus/S 210", "EC"), ("S210", "EC"), ("S 210", "EC"),
        ("Response/R 1", None),
    ],
)
def test_marker_normalization(text, expected):
    assert normalize_rest_marker(text) == expected


def _annotations(onsets, descriptions):
    return SimpleNamespace(
        onset=np.asarray(onsets, dtype=float),
        description=np.asarray(descriptions, dtype=object),
    )


def test_parse_rest_blocks_uses_marker_to_next_marker_and_last_to_recording_end():
    blocks = parse_rest_blocks(
        _annotations([0.0, 60.0, 120.0, 180.0], ["S200", "S210", "S200", "S210"]),
        duration_s=240.0,
    )
    assert [(b.condition, b.start_s, b.stop_s) for b in blocks] == [
        ("EO", 0.0, 60.0), ("EC", 60.0, 120.0),
        ("EO", 120.0, 180.0), ("EC", 180.0, 240.0),
    ]


def test_parse_rest_blocks_rejects_non_alternating_or_nonincreasing_markers():
    with pytest.raises(ValueError, match="alternate"):
        parse_rest_blocks(_annotations([0, 60, 120], ["S200", "S200", "S210"]), 180.0)
    with pytest.raises(ValueError, match="increasing"):
        parse_rest_blocks(_annotations([0, 120, 60], ["S200", "S210", "S200"]), 180.0)


class _FakeRaw:
    def __init__(self, sfreq=100.0):
        self.info = {"sfreq": sfreq}
        self.ch_names = ["Fz", "Cz"]
        self.annotations = _annotations(
            [0, 25, 50, 75, 100, 125, 150, 175],
            ["S200", "S210", "S200", "S210", "S200", "S210", "S200", "S210"],
        )
        t = np.arange(int(200 * sfreq)) / sfreq
        self._data = np.vstack([np.sin(2*np.pi*10*t), np.sin(2*np.pi*6*t + 0.2)])
        self.times = t

    def get_data(self, start=None, stop=None):
        return self._data[:, slice(start, stop)]


def test_feature_blocks_from_raw_keeps_physical_blocks_separate_and_requires_four_per_condition():
    result = feature_blocks_from_raw(_FakeRaw(), epoch_s=0.5, fs=100.0)
    assert set(result) == {"EC", "EO"}
    assert len(result["EC"].blocks) == 4
    assert len(result["EO"].blocks) == 4
    assert all(block.shape[0] >= 43 for condition in result.values() for block in condition.blocks)
    assert all(np.all(np.isfinite(block)) for condition in result.values() for block in condition.blocks)
    assert result["EC"].blocks[0] is not result["EC"].blocks[1]


def test_feature_blocks_from_raw_rejects_short_blocks():
    raw = _FakeRaw()
    raw.annotations = _annotations([0, 10, 20, 30, 40, 50, 60, 70], ["S200","S210"]*4)
    with pytest.raises(ValueError, match="fewer than four"):
        feature_blocks_from_raw(raw, epoch_s=0.5, fs=100.0)


def test_discover_subjects_prefers_unique_resting_header(tmp_path):
    from brainloops.datasets.lemon import discover_subjects

    rest_dir = tmp_path / "sub-010005" / "eeg"
    rest_dir.mkdir(parents=True)
    rest = rest_dir / "sub-010005_task-resting_eeg.vhdr"
    other = rest_dir / "sub-010005_task-oddball_eeg.vhdr"
    rest.write_text("Brain Vision Data Exchange Header File Version 1.0\n", encoding="utf-8")
    other.write_text("Brain Vision Data Exchange Header File Version 1.0\n", encoding="utf-8")
    subjects = discover_subjects(tmp_path)
    assert [(s.subject_id, s.vhdr_path.name) for s in subjects] == [
        ("sub-010005", "sub-010005_task-resting_eeg.vhdr")
    ]


def test_load_subject_conditions_scales_once_per_condition(monkeypatch, tmp_path):
    import brainloops.datasets.lemon as lemon

    raw = _FakeRaw()
    monkeypatch.setattr(lemon.mne.io, "read_raw_brainvision", lambda *a, **k: raw)
    monkeypatch.setattr(lemon.mne, "pick_types", lambda *a, **k: np.array([0, 1]))
    raw.pick = lambda picks: raw
    raw.rename_channels = lambda mapping: None
    raw.resample = lambda fs, verbose=False: raw

    calls = []
    real_scale = lemon.robust_scale_clip

    def counting_scale(X, *args, **kwargs):
        calls.append(np.asarray(X).shape[0])
        return real_scale(X, *args, **kwargs)

    monkeypatch.setattr(lemon, "robust_scale_clip", counting_scale)
    subject = lemon.LEMONSubject("sub-010005", tmp_path / "dummy.vhdr")
    result = lemon.load_subject_conditions(subject, epoch_s=0.5, fs=100.0)
    assert set(result) == {"EO", "EC"}
    assert sorted(calls) == [200, 200]
    assert all(len(result[c].blocks) == 4 for c in ("EO", "EC"))


def test_load_subject_conditions_keeps_usable_condition_when_other_has_too_few_blocks(monkeypatch, tmp_path):
    import brainloops.datasets.lemon as lemon

    raw = _FakeRaw()
    raw.annotations = _annotations(
        [0, 25, 50, 75, 100, 125, 150],
        ["S210", "S200", "S210", "S200", "S210", "S200", "S210"],
    )
    monkeypatch.setattr(lemon.mne.io, "read_raw_brainvision", lambda *a, **k: raw)
    monkeypatch.setattr(lemon.mne, "pick_types", lambda *a, **k: np.array([0, 1]))
    raw.pick = lambda picks: raw
    raw.rename_channels = lambda mapping: None
    raw.resample = lambda fs, verbose=False: raw
    result = lemon.load_subject_conditions(lemon.LEMONSubject("sub-010007", tmp_path / "dummy.vhdr"))
    assert set(result) == {"EC"}
    assert len(result["EC"].blocks) == 4


def test_discovery_requires_literal_sub_path_component(tmp_path):
    from brainloops.datasets.lemon import discover_subjects
    d = tmp_path / "misc"
    d.mkdir()
    (d / "sub-010008_task-resting_eeg.vhdr").write_text("header", encoding="utf-8")
    assert discover_subjects(tmp_path) == []


def test_load_subject_conditions_preserves_valid_ec_when_eo_is_constant(monkeypatch, tmp_path):
    import brainloops.datasets.lemon as lemon

    raw = _FakeRaw()
    # Every EO block is constant; all EC blocks retain their original signal.
    for block in lemon.parse_rest_blocks(raw):
        if block.condition == "EO":
            start = int(block.start_s * 100)
            stop = int(block.stop_s * 100)
            raw._data[:, start:stop] = 0.0
    monkeypatch.setattr(lemon.mne.io, "read_raw_brainvision", lambda *a, **k: raw)
    monkeypatch.setattr(lemon.mne, "pick_types", lambda *a, **k: np.array([0, 1]))
    raw.pick = lambda picks: raw
    raw.rename_channels = lambda mapping: None
    raw.resample = lambda fs, verbose=False: raw
    result = lemon.load_subject_conditions(lemon.LEMONSubject("sub-010007", tmp_path / "dummy.vhdr"))
    assert set(result) == {"EC"}
    assert len(result["EC"].blocks) == 4
    assert all(np.any(np.ptp(batch.X, axis=0) > 0) for batch in result["EC"].blocks)
