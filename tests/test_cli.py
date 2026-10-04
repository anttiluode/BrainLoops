from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from brainloops.types import FeatureBatch
from brainloops.probe import probe_features
import brainloops.cli as cli


def test_module_help_lists_probe_gate0_and_gate1():
    result = subprocess.run(
        [sys.executable, "-m", "brainloops.cli", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "probe" in result.stdout
    assert "gate0" in result.stdout
    assert "gate1" in result.stdout


def test_bad_probe_path_returns_nonzero_with_concise_error(capsys):
    rc = cli.main(["probe", "/definitely/not/a/recording.edf"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "error:" in captured.err.lower()
    assert "recording.edf" in captured.err


def test_probe_command_outputs_expected_json_sections(monkeypatch, tmp_path, capsys):
    recording = tmp_path / "recording.edf"
    recording.touch()
    monkeypatch.setattr(
        cli,
        "probe_edf",
        lambda *args, **kwargs: {
            "artifact_stats": {"fraction_values_clipped": 0.01},
            "discrete": {"classification": "LINEAR_LAG_RECURRENCE", "rows": []},
            "continuous": {"train_r2": 0.5, "modes": []},
        },
    )
    rc = cli.main(["probe", str(recording)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(payload) >= {"artifact_stats", "discrete", "continuous"}


def test_probe_features_reports_discrete_and_continuous_measurements():
    t = np.arange(240)
    phase = 2 * np.pi * t / 16
    X = np.c_[np.cos(phase), np.sin(phase), np.cos(phase + 0.3)]
    batch = FeatureBatch(X=X, epoch_s=0.5, feature_names=("a", "b", "c"))
    payload = probe_features(batch, ks=(6, 10), n_null=3, seed=0)
    assert payload["discrete"]["classification"] in {
        "NO_ROBUST_RECURRENCE",
        "LINEAR_LAG_RECURRENCE",
        "BEYOND_LINEAR_RECURRENCE",
    }
    assert len(payload["discrete"]["rows"]) == 2
    assert np.isfinite(payload["continuous"]["train_r2"])
    assert payload["continuous"]["modes"]
