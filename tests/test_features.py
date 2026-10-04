import numpy as np
import pytest

from brainloops.features import bandpower_epochs, robust_scale_clip


def test_robust_scale_reports_values_not_any_feature_epochs():
    X = np.zeros((10, 100))
    X[0, 0] = 100
    Y, stats = robust_scale_clip(X, clip=4.0, epoch_extreme_fraction=0.10)
    assert stats.n_epochs == 10
    assert stats.n_values == 1000
    assert stats.epochs_over_extreme_fraction == 0
    assert stats.values_clipped > 0
    assert np.max(np.abs(Y)) <= 4.0


def test_robust_scale_rejects_too_short_input():
    with pytest.raises(ValueError):
        robust_scale_clip(np.zeros((1, 20)))


def test_robust_scale_rejects_fully_constant_input():
    with pytest.raises(ValueError):
        robust_scale_clip(np.zeros((4, 20)))


def test_bandpower_alpha_sine_beats_delta_and_uses_half_second_epochs():
    sfreq = 100.0
    epoch_s = 0.5
    t = np.arange(0, 2.0, 1.0 / sfreq)
    data = np.sin(2 * np.pi * 10.0 * t)[None, :]
    batch = bandpower_epochs(data, sfreq=sfreq, epoch_s=epoch_s)
    assert batch.X.shape[0] == 4
    assert batch.epoch_s == 0.5
    alpha_idx = batch.feature_names.index("ch0-alpha")
    delta_idx = batch.feature_names.index("ch0-delta")
    assert np.mean(batch.X[:, alpha_idx]) > np.mean(batch.X[:, delta_idx])


def test_bandpower_rejects_recording_shorter_than_two_epochs():
    with pytest.raises(ValueError):
        bandpower_epochs(np.zeros((2, 90)), sfreq=100.0, epoch_s=0.5)
