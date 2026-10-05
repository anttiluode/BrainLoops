from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
from scipy.stats import pearsonr, spearmanr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brainloops import __version__
from brainloops.datasets.lemon import discover_subjects, load_subject_conditions
from brainloops.receipts import config_fingerprint, write_receipt
from brainloops.transition_recurrence import (
    classify_recurrence_tier,
    evaluate_subject_condition,
    interpret_transition_vs_state,
    permutation_p_value,
    population_rule,
)

MetricName = Literal["transition", "state"]
NullKind = Literal["order", "phase"]


def is_development_subject(subject_id: str) -> bool:
    digest = hashlib.sha256(("brainloops-r1:" + str(subject_id)).encode("utf-8")).hexdigest()
    return int(digest, 16) % 5 == 0


def _metric_to_dict(metric) -> dict[str, object]:
    if is_dataclass(metric):
        raw = asdict(metric)
    else:
        raw = dict(metric)
    out = dict(raw)
    for key in ("order_null", "phase_null"):
        if key in out:
            out[key] = np.asarray(out[key], dtype=float).tolist()
    return out


def aggregate_population(
    subject_rows: Sequence[dict],
    metric: MetricName,
    null_kind: NullKind,
    n_null: int,
) -> dict[str, object]:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    if not subject_rows:
        raise ValueError("at least one subject row is required")
    null_key = f"{null_kind}_null"
    real = np.asarray([float(row[metric]["real"]) for row in subject_rows], dtype=float)
    nulls = np.asarray([row[metric][null_key] for row in subject_rows], dtype=float)
    if nulls.shape != (len(subject_rows), n_null):
        raise ValueError("subject null arrays do not match n_null")
    real_median = float(np.median(real))
    null_aggregate = np.median(nulls, axis=0)
    p = permutation_p_value(real_median, null_aggregate)
    positive = np.asarray([real[i] > float(np.median(nulls[i])) + 1e-12 for i in range(len(real))], dtype=bool)
    positive_fraction = float(np.mean(positive))
    passed = population_rule(p, positive_fraction)
    return {
        "real_median": real_median,
        "null_aggregate": null_aggregate.tolist(),
        "null_median": float(np.median(null_aggregate)),
        "p_value": p,
        "positive_fraction": positive_fraction,
        "positive_count": int(np.sum(positive)),
        "n_subjects": int(len(subject_rows)),
        "pass": bool(passed),
    }


def _status_from_rows(rows: Sequence[dict], n_null: int, *, min_subjects: int = 20) -> dict[str, object]:
    if n_null < 19 or len(rows) < min_subjects:
        return {
            "status": "INSUFFICIENT_DATA",
            "n_subjects": len(rows),
            "transition_class": "NO_ROBUST_RECURRENCE",
            "state_class": "NO_ROBUST_RECURRENCE",
            "interpretation": "NO_ROBUST_RECURRENCE",
        }
    aggregates = {}
    passes = {}
    for metric in ("transition", "state"):
        for null_kind in ("order", "phase"):
            key = f"{metric}_{null_kind}"
            aggregates[key] = aggregate_population(rows, metric, null_kind, n_null)
            passes[key] = bool(aggregates[key]["pass"])
    transition_order = passes["transition_order"]
    transition_phase = transition_order and passes["transition_phase"]
    state_order = passes["state_order"]
    state_phase = state_order and passes["state_phase"]
    transition_class = classify_recurrence_tier(transition_order, transition_phase)
    state_class = classify_recurrence_tier(state_order, state_phase)
    if transition_phase:
        status = "PASS_BEYOND_LINEAR"
    elif transition_order:
        status = "PASS_LINEAR"
    else:
        status = "FAIL"
    return {
        "status": status,
        "n_subjects": len(rows),
        "transition_class": transition_class,
        "state_class": state_class,
        "interpretation": interpret_transition_vs_state(transition_class, state_class),
        "aggregates": aggregates,
    }


def primary_ec_status(rows: Sequence[dict], n_null: int) -> dict[str, object]:
    heldout_ec = [row for row in rows if row.get("split") == "heldout" and row.get("condition") == "EC" and "transition" in row]
    return _status_from_rows(heldout_ec, n_null)


def exploratory_ec_status(rows: Sequence[dict], n_null: int) -> dict[str, object]:
    heldout_ec = [row for row in rows if row.get("split") == "heldout" and row.get("condition") == "EC" and "transition" in row]
    return _status_from_rows(heldout_ec, n_null, min_subjects=1)


def artifact_diagnostics(rows: Sequence[dict]) -> dict[str, float | None]:
    x = []
    y = []
    for row in rows:
        try:
            artifact = float(row["artifact_stats"]["fraction_values_clipped"])
            metric = row["transition"]
            effect = float(metric["real"]) - float(np.median(np.asarray(metric["order_null"], dtype=float)))
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(artifact) and np.isfinite(effect):
            x.append(artifact)
            y.append(effect)
    if len(x) < 3 or np.ptp(x) <= 1e-15 or np.ptp(y) <= 1e-15:
        return {"pearson_r": None, "spearman_r": None, "n": len(x)}
    return {
        "pearson_r": float(pearsonr(x, y).statistic),
        "spearman_r": float(spearmanr(x, y).statistic),
        "n": len(x),
    }


def _stable_condition_seed(seed: int, subject_id: str, condition: str) -> int:
    digest = hashlib.sha256(f"brainloops-r1-seed:{seed}:{subject_id}:{condition}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32)


def _load_resume(path: Path, fingerprint: str) -> dict | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("config_fingerprint") != fingerprint:
        raise ValueError("resume receipt config fingerprint does not match requested run")
    return payload


def _row_from_result(subject_id: str, split: str, condition: str, condition_features, result) -> dict[str, object]:
    return {
        "subject_id": subject_id,
        "split": split,
        "condition": condition,
        "usable_blocks": len(condition_features.blocks),
        "artifact_stats": asdict(condition_features.artifact_stats),
        "transition": _metric_to_dict(result.transition),
        "state": _metric_to_dict(result.state),
        "transition_class": result.transition_class,
        "state_class": result.state_class,
        "interpretation": result.interpretation,
        "transition_spectrum": np.asarray(result.transition_spectrum, dtype=float).tolist(),
        "state_spectrum": np.asarray(result.state_spectrum, dtype=float).tolist(),
    }


def run_r1(
    data: str | Path,
    subject_ids: Sequence[str] | None = None,
    n_null: int = 99,
    output: str | Path | None = None,
    resume: bool = False,
    seed: int = 0,
    exploratory: bool = False,
    retry_skipped: bool = False,
) -> dict[str, object]:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    subjects = sorted(discover_subjects(data, subject_ids=subject_ids), key=lambda x: x.subject_id)
    if not subjects:
        raise ValueError(
            f"No eligible raw LEMON subjects found in {data}. "
            "r1-lemon requires BrainVision .vhdr files inside sub-... folders "
            "with their .vmrk and .eeg companions. EEGMMIDB EDF recordings "
            "are inputs for gate1/gate1b/gate1c. Check --data and any --subjects filter."
        )
    config = {
        "code_version": __version__,
        "seed": int(seed),
        "n_null": int(n_null),
        "epoch_s": 0.5,
        "half_window": 1,
        "lag_min_s": 2.0,
        "lag_max_s": 20.0,
        "lag_step_s": 0.5,
        "pca_dim": 8,
        "primary_condition": "EC",
        "replication_condition": "EO",
        "subject_ids": [s.subject_id for s in subjects],
    }
    if exploratory:
        config["exploratory"] = True
    fingerprint = config_fingerprint(config)
    output_path = None if output is None else Path(output)
    existing = _load_resume(output_path, fingerprint) if resume and output_path is not None else None
    rows = [] if existing is None else list(existing.get("subject_conditions", []))
    if retry_skipped:
        rows = [row for row in rows if row.get("status") != "SKIP"]
    done = {(r["subject_id"], r["condition"]) for r in rows}

    development = [s.subject_id for s in subjects if is_development_subject(s.subject_id)]
    heldout = [s.subject_id for s in subjects if not is_development_subject(s.subject_id)]
    payload: dict[str, object] = {
        "gate": "r1_lemon_resting_transition_recurrence",
        "status": "IN_PROGRESS",
        "config": config,
        "config_fingerprint": fingerprint,
        "development_subjects": development,
        "heldout_subjects": heldout,
        "subject_conditions": rows,
    }
    if output_path is not None and (existing is None or retry_skipped):
        write_receipt(output_path, payload)

    for subject in subjects:
        needed = [c for c in ("EC", "EO") if (subject.subject_id, c) not in done]
        if not needed:
            continue
        split = "development" if is_development_subject(subject.subject_id) else "heldout"
        condition_errors: dict[str, str] = {}
        try:
            condition_map = load_subject_conditions(
                subject, epoch_s=0.5, fs=100.0, condition_errors=condition_errors
            )
        except (ValueError, FileNotFoundError) as exc:
            for condition in needed:
                rows.append({
                    "subject_id": subject.subject_id,
                    "split": split,
                    "condition": condition,
                    "status": "SKIP",
                    "reason": str(exc),
                })
                done.add((subject.subject_id, condition))
            payload["subject_conditions"] = rows
            if output_path is not None:
                write_receipt(output_path, payload)
            continue
        for condition in ("EC", "EO"):
            if condition not in needed:
                continue
            if condition not in condition_map:
                rows.append({
                    "subject_id": subject.subject_id,
                    "split": split,
                    "condition": condition,
                    "status": "SKIP",
                    "reason": condition_errors.get(
                        condition, "condition has fewer than four usable physical blocks"
                    ),
                })
                done.add((subject.subject_id, condition))
                payload["subject_conditions"] = rows
                if output_path is not None:
                    write_receipt(output_path, payload)
                continue
            cf = condition_map[condition]
            blocks = [batch.X for batch in cf.blocks]
            try:
                result = evaluate_subject_condition(
                    blocks,
                    n_null=n_null,
                    seed=_stable_condition_seed(seed, subject.subject_id, condition),
                    epoch_s=0.5,
                    half_window=1,
                )
            except ValueError as exc:
                row = {
                    "subject_id": subject.subject_id,
                    "split": split,
                    "condition": condition,
                    "status": "SKIP",
                    "reason": str(exc),
                }
            else:
                row = _row_from_result(subject.subject_id, split, condition, cf, result)
            rows.append(row)
            done.add((subject.subject_id, condition))
            payload["subject_conditions"] = rows
            if output_path is not None:
                write_receipt(output_path, payload)

    primary = primary_ec_status(rows, n_null)
    heldout_eo = [r for r in rows if r.get("split") == "heldout" and r.get("condition") == "EO" and "transition" in r]
    replication = _status_from_rows(heldout_eo, n_null)
    heldout_ec = [r for r in rows if r.get("split") == "heldout" and r.get("condition") == "EC" and "transition" in r]
    payload.update(
        {
            "status": primary["status"],
            "primary_ec": primary,
            "replication_eo": replication,
            "artifact_diagnostics_ec": artifact_diagnostics(heldout_ec),
        }
    )
    if exploratory:
        exploratory_ec = exploratory_ec_status(rows, n_null)
        payload.update({
            "status": "EXPLORATORY_" + exploratory_ec["status"],
            "canonical_status": primary["status"],
            "exploratory_ec": exploratory_ec,
            "exploratory_eo": _status_from_rows(heldout_eo, n_null, min_subjects=1),
        })
    if output_path is not None:
        write_receipt(output_path, payload)
    return payload


def print_run_summary(payload: dict[str, object]) -> None:
    print(payload["status"])
    exploratory = "exploratory_ec" in payload
    if exploratory:
        print(f"Canonical R1 status: {payload['canonical_status']} (requires 20 usable held-out EC subjects)")
        print("Exploratory analysis: small sample; not the canonical population gate.")
    if payload["status"] == "INSUFFICIENT_DATA" or exploratory:
        config = payload["config"]
        print(f"Discovered LEMON subjects: {len(config['subject_ids'])}")
        requirement = "exploratory minimum: 1" if exploratory else "required: 20"
        print(f"Usable held-out EC subjects: {payload['primary_ec']['n_subjects']} ({requirement})")
        print(f"Null replicates: {config['n_null']} (required: 19)")
        skipped = [row for row in payload["subject_conditions"] if row.get("status") == "SKIP"]
        print(f"Skipped subject-conditions: {len(skipped)}")
        reasons = Counter(str(row.get("reason", "unknown reason")) for row in skipped)
        for reason, count in reasons.most_common(5):
            print(f"  Skip reason ({count} condition(s)): {reason}")
        if len(reasons) > 5:
            print("  Additional skip reasons are retained in the receipt.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BrainLoops R1 on LEMON resting EEG")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subjects", nargs="*")
    parser.add_argument("--n-null", type=int, default=99)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--exploratory", action="store_true", help="report a labeled small-sample analysis while retaining the canonical 20-subject status")
    parser.add_argument("--retry-skipped", action="store_true", help="retry skipped conditions when resuming, retaining completed results")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    try:
        payload = run_r1(args.data, subject_ids=args.subjects, n_null=args.n_null, output=args.output, resume=args.resume, seed=args.seed, exploratory=args.exploratory, retry_skipped=args.retry_skipped)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print_run_summary(payload)
    return 0 if payload["status"].removeprefix("EXPLORATORY_") in {"PASS_LINEAR", "PASS_BEYOND_LINEAR", "FAIL", "INSUFFICIENT_DATA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
