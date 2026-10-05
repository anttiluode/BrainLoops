from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pytest

import experiments.r1_lemon as r1
from brainloops.features import ArtifactStats, FeatureBatch
from brainloops.transition_recurrence import MetricNullResult, SubjectConditionResult


def test_deterministic_subject_split_preserves_literal_identifier():
    expected = {
        "sub-010002": False,
        "sub-010003": True,
        "sub-010004": False,
        "sub-010005": False,
    }
    assert {k: r1.is_development_subject(k) for k in expected} == expected
    assert r1.is_development_subject("sub-000001") is False
    assert r1.is_development_subject("sub-1") is True


def _row(subject, real, null, *, positive=None, metric="transition"):
    if positive is None:
        positive = real > float(np.median(null))
    other_real = real - 10.0
    other_null = np.asarray(null) - 10.0
    return {
        "subject_id": subject,
        "condition": "EC",
        "split": "heldout",
        metric: {"real": real, "order_null": list(null), "phase_null": list(null), "positive_order": positive, "positive_phase": positive},
        ("state" if metric == "transition" else "transition"): {"real": other_real, "order_null": list(other_null), "phase_null": list(other_null), "positive_order": False, "positive_phase": False},
    }


def test_population_aggregation_uses_subject_median_and_replicate_aligned_nulls():
    rows = [
        _row("sub-a", 1.0, [1.0, 7.0, 2.0]),
        _row("sub-b", 6.0, [2.0, 8.0, 3.0]),
        _row("sub-c", 7.0, [3.0, 9.0, 4.0]),
    ]
    out = r1.aggregate_population(rows, "transition", "order", n_null=3)
    assert out["real_median"] == 6.0
    assert out["null_aggregate"] == [2.0, 8.0, 3.0]
    assert out["p_value"] == 0.5
    assert out["positive_fraction"] == 2 / 3
    assert out["pass"] is False


def test_canonical_status_requires_20_heldout_ec_and_19_nulls():
    rows = [_row(f"sub-{i:02d}", 5.0, [0.0] * 19) for i in range(19)]
    assert r1.primary_ec_status(rows, n_null=19)["status"] == "INSUFFICIENT_DATA"
    rows.append(_row("sub-20", 5.0, [0.0] * 19))
    assert r1.primary_ec_status(rows, n_null=18)["status"] == "INSUFFICIENT_DATA"
    result = r1.primary_ec_status(rows, n_null=19)
    assert result["status"] == "PASS_BEYOND_LINEAR"
    assert result["transition_class"] == "BEYOND_LINEAR_RECURRENCE"


@dataclass(frozen=True)
class _Subject:
    subject_id: str
    vhdr_path: Path


def _features(subject_id: str, condition: str):
    rng = np.random.default_rng(abs(hash((subject_id, condition))) % 10000)
    batches = tuple(FeatureBatch(rng.normal(size=(50, 4)), 0.5, ("a","b","c","d")) for _ in range(4))
    stats = ArtifactStats(200, 800, 8, 0.01, 2, 0.01)
    return type("F", (), {"subject_id": subject_id, "condition": condition, "blocks": batches, "artifact_stats": stats})()


def _fake_result(seed=0):
    null = np.zeros(19)
    metric = MetricNullResult(1.0, 4.0, null, null, 0.05, 0.05, True, True)
    return SubjectConditionResult(metric, metric, "BEYOND_LINEAR_RECURRENCE", "BEYOND_LINEAR_RECURRENCE", "JOINT_TRANSITION_AND_STATE_RECURRENCE", np.ones(37), np.ones(37))


def test_run_r1_records_split_conditions_and_resume(monkeypatch, tmp_path):
    subjects = [_Subject(f"sub-{i:06d}", tmp_path / f"s{i}.vhdr") for i in range(1, 31)]
    loads = []
    monkeypatch.setattr(r1, "discover_subjects", lambda *a, **k: subjects)
    monkeypatch.setattr(r1, "load_subject_conditions", lambda s, **k: (loads.append(s.subject_id) or {"EC": _features(s.subject_id,"EC"), "EO": _features(s.subject_id,"EO")}))
    monkeypatch.setattr(r1, "evaluate_subject_condition", lambda *a, **k: _fake_result())
    output = tmp_path / "receipt.json"
    payload = r1.run_r1(tmp_path, n_null=19, output=output, resume=False, seed=7)
    assert payload["gate"] == "r1_lemon_resting_transition_recurrence"
    assert payload["config_fingerprint"]
    assert payload["development_subjects"]
    assert payload["heldout_subjects"]
    assert {row["condition"] for row in payload["subject_conditions"]} == {"EC", "EO"}
    assert payload["primary_ec"]["status"] in {"PASS_LINEAR", "PASS_BEYOND_LINEAR", "FAIL", "INSUFFICIENT_DATA"}
    assert "replication_eo" in payload
    first_load_count = len(loads)
    resumed = r1.run_r1(tmp_path, n_null=19, output=output, resume=True, seed=7)
    assert len(loads) == first_load_count
    assert resumed["config_fingerprint"] == payload["config_fingerprint"]


def test_artifact_diagnostics_return_none_for_constants():
    rows = []
    for i in range(20):
        row = _row(f"sub-{i}", 1.0, [0.0] * 19)
        row["artifact_stats"] = {"fraction_values_clipped": 0.1}
        rows.append(row)
    out = r1.artifact_diagnostics(rows)
    assert out["pearson_r"] is None
    assert out["spearman_r"] is None


def test_runner_records_invalid_subject_as_skip_and_continues(monkeypatch, tmp_path):
    subjects = [_Subject("sub-000001", tmp_path / "a.vhdr"), _Subject("sub-000002", tmp_path / "b.vhdr")]
    monkeypatch.setattr(r1, "discover_subjects", lambda *a, **k: subjects)
    def load(subject, **kwargs):
        if subject.subject_id == "sub-000001":
            raise ValueError("malformed rest markers")
        return {"EC": _features(subject.subject_id, "EC"), "EO": _features(subject.subject_id, "EO")}
    monkeypatch.setattr(r1, "load_subject_conditions", load)
    monkeypatch.setattr(r1, "evaluate_subject_condition", lambda *a, **k: _fake_result())
    payload = r1.run_r1(tmp_path, n_null=19, output=tmp_path / "r.json", seed=0)
    skipped = [row for row in payload["subject_conditions"] if row.get("status") == "SKIP"]
    completed = [row for row in payload["subject_conditions"] if "transition" in row]
    assert {(row["subject_id"], row["condition"]) for row in skipped} == {
        ("sub-000001", "EC"), ("sub-000001", "EO")
    }
    assert {(row["subject_id"], row["condition"]) for row in completed} == {
        ("sub-000002", "EC"), ("sub-000002", "EO")
    }
    assert "malformed rest markers" in skipped[0]["reason"]


def test_runner_skips_degenerate_condition_and_resumes_without_repeating_it(monkeypatch, tmp_path):
    subjects = [_Subject("sub-000001", tmp_path / "a.vhdr"), _Subject("sub-000002", tmp_path / "b.vhdr")]
    loads = []
    monkeypatch.setattr(r1, "discover_subjects", lambda *a, **k: subjects)

    def load(subject, **kwargs):
        loads.append(subject.subject_id)
        conditions = {c: _features(subject.subject_id, c) for c in ("EC", "EO")}
        if subject.subject_id == "sub-000001":
            rank_one = np.column_stack((np.linspace(-1.0, 1.0, 50), np.zeros((50, 3))))
            conditions["EC"].blocks = tuple(
                FeatureBatch(rank_one.copy(), 0.5, ("a", "b", "c", "d")) for _ in range(4)
            )
        return conditions

    monkeypatch.setattr(r1, "load_subject_conditions", load)
    output = tmp_path / "receipt.json"
    payload = r1.run_r1(tmp_path, n_null=1, output=output)
    rows = payload["subject_conditions"]
    skipped = [row for row in rows if row.get("status") == "SKIP"]
    assert [(row["subject_id"], row["condition"]) for row in skipped] == [("sub-000001", "EC")]
    assert "PCA component variance" in skipped[0]["reason"]
    assert {(row["subject_id"], row["condition"]) for row in rows if "transition" in row} == {
        ("sub-000001", "EO"), ("sub-000002", "EC"), ("sub-000002", "EO")
    }
    assert json.loads(output.read_text())["subject_conditions"] == rows
    resumed = r1.run_r1(tmp_path, n_null=1, output=output, resume=True)
    assert loads == ["sub-000001", "sub-000002"]
    assert resumed["subject_conditions"] == rows


def test_runner_persists_split_before_first_recording_can_be_interrupted(monkeypatch, tmp_path):
    subject = _Subject("sub-010002", tmp_path / "a.vhdr")
    monkeypatch.setattr(r1, "discover_subjects", lambda *a, **k: [subject])

    def interrupted_load(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(r1, "load_subject_conditions", interrupted_load)
    output = tmp_path / "receipt.json"
    with pytest.raises(KeyboardInterrupt):
        r1.run_r1(tmp_path, n_null=19, output=output)
    checkpoint = json.loads(output.read_text())
    assert checkpoint["status"] == "IN_PROGRESS"
    assert checkpoint["heldout_subjects"] == ["sub-010002"]
    assert checkpoint["development_subjects"] == []
    assert checkpoint["subject_conditions"] == []
    assert checkpoint["config_fingerprint"]
