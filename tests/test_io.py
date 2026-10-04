from pathlib import Path

import mne
import numpy as np
import pytest

from brainloops.io import load_edf_features, normalize_channel_name, select_region


def test_normalize_channel_name_handles_whitespace_case_and_dots():
    assert normalize_channel_name(" Oz. ") == "OZ"
    assert normalize_channel_name("po.z") == "POZ"
    assert normalize_channel_name(" fP1 ") == "FP1"


def test_select_region_returns_matching_indices_and_rejects_missing_region():
    names = ["O1", "O2", "C3"]
    assert select_region(names, "Occipital") == [0, 1]
    with pytest.raises(ValueError, match="No Temporal channels"):
        select_region(names, "Temporal")


def test_load_edf_features_normalizes_names_and_reports_artifacts(monkeypatch):
    sfreq = 100.0
    t = np.arange(0, 4.0, 1 / sfreq)
    rng = np.random.default_rng(1)
    data = np.vstack([
        np.sin(2 * np.pi * 10 * t),
        0.5 * np.sin(2 * np.pi * 6 * t),
        np.sin(2 * np.pi * 20 * t),
    ]) + 0.01 * rng.normal(size=(3, t.size))
    raw = mne.io.RawArray(data, mne.create_info(["O1.", "O2.", "C3."], sfreq, ch_types="eeg"), verbose=False)
    monkeypatch.setattr(mne.io, "read_raw_edf", lambda *args, **kwargs: raw.copy())

    batch = load_edf_features(Path("fake.edf"), region="Occipital", epoch_s=0.5, fs=100.0)

    assert batch.X.shape == (8, 10)
    assert batch.feature_names[0] == "O1-delta"
    assert batch.feature_names[5] == "O2-delta"
    assert np.all(np.isfinite(batch.X))
    assert batch.artifact_stats is not None
    assert batch.artifact_stats.n_epochs == 8


def test_load_edf_features_fails_when_region_absent(monkeypatch):
    raw = mne.io.RawArray(np.random.default_rng(0).normal(size=(1, 400)), mne.create_info(["C3."], 100.0, ch_types="eeg"), verbose=False)
    monkeypatch.setattr(mne.io, "read_raw_edf", lambda *args, **kwargs: raw.copy())
    with pytest.raises(ValueError, match="No Occipital channels"):
        load_edf_features("fake.edf", region="Occipital")
