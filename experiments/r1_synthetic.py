from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brainloops import __version__
from brainloops.receipts import config_fingerprint, write_receipt
from brainloops.transition_recurrence import evaluate_subject_condition


def _iid_blocks(seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.normal(size=(180, 4)) for _ in range(4)]


def _linear_rotation_blocks(seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    theta = 2 * np.pi / 12.0
    A = 0.98 * np.array(
        [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    )
    blocks: list[np.ndarray] = []
    for _ in range(4):
        x = np.zeros((240, 2), dtype=float)
        x[0] = rng.normal(size=2)
        for t in range(1, len(x)):
            x[t] = A @ x[t - 1] + 0.35 * rng.normal(size=2)
        blocks.append(np.c_[x, 0.5 * rng.normal(size=(240, 2))])
    return blocks


def _drifting_repeated_transform_blocks(seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    period = 12
    dims = 4
    phase = np.arange(period - 2, dtype=float)
    planted = 20.0 * np.stack(
        [
            np.cos(2 * np.pi * phase / (period - 2)),
            np.sin(2 * np.pi * phase / (period - 2)),
            np.cos(4 * np.pi * phase / (period - 2)),
            np.sin(4 * np.pi * phase / (period - 2)),
        ],
        axis=1,
    )
    blocks: list[np.ndarray] = []
    for _ in range(4):
        rows: list[np.ndarray] = []
        for _cycle in range(24):
            cycle = np.zeros((period, dims), dtype=float)
            cycle[0] = rng.normal(size=dims)
            cycle[1] = rng.normal(size=dims)
            for p in range(period - 2):
                cycle[p + 2] = cycle[p] + planted[p]
            rows.extend(cycle)
        blocks.append(np.asarray(rows, dtype=float))
    return blocks


def _state_return_variable_direction_blocks(seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    period = 40
    phase = np.arange(period, dtype=float)
    center = np.stack(
        [
            np.cos(2 * np.pi * phase / period),
            np.sin(2 * np.pi * phase / period),
            np.cos(4 * np.pi * phase / period),
            np.sin(4 * np.pi * phase / period),
        ],
        axis=1,
    )
    blocks: list[np.ndarray] = []
    for _ in range(4):
        repeated = np.tile(center, (8, 1))
        blocks.append(repeated + 2.0 * rng.normal(size=repeated.shape))
    return blocks


def synthetic_cases(seed: int) -> dict[str, list[np.ndarray]]:
    return {
        "iid_noise": _iid_blocks(seed),
        "linear_rotation": _linear_rotation_blocks(seed),
        "drifting_repeated_transform": _drifting_repeated_transform_blocks(seed),
        "state_return_variable_direction": _state_return_variable_direction_blocks(seed),
    }


def _result_payload(result) -> dict[str, object]:
    return {
        "transition_class": result.transition_class,
        "state_class": result.state_class,
        "interpretation": result.interpretation,
        "transition": asdict(result.transition),
        "state": asdict(result.state),
    }


def _case_passes(name: str, payload: dict[str, object]) -> bool:
    t = str(payload["transition_class"])
    z = str(payload["state_class"])
    interpretation = str(payload["interpretation"])
    rank = {
        "NO_ROBUST_RECURRENCE": 0,
        "LINEAR_LAG_RECURRENCE": 1,
        "BEYOND_LINEAR_RECURRENCE": 2,
    }
    if name == "iid_noise":
        return t == "NO_ROBUST_RECURRENCE"
    if name == "linear_rotation":
        return t == "LINEAR_LAG_RECURRENCE"
    if name == "drifting_repeated_transform":
        return rank[t] >= 1 and rank[t] > rank[z] and interpretation.startswith("TRANSFORMATION_ONLY")
    if name == "state_return_variable_direction":
        return rank[z] > rank[t] and interpretation == "STATE_RECURRENCE_DOMINANT"
    raise ValueError(name)


def run_r1_synthetic(seed: int = 1, n_null: int = 99) -> dict[str, object]:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    config = {
        "seed": int(seed),
        "n_null": int(n_null),
        "epoch_s": 0.5,
        "half_window": 1,
        "lag_min_s": 2.0,
        "lag_max_s": 20.0,
        "lag_step_s": 0.5,
        "code_version": __version__,
    }
    cases: dict[str, object] = {}
    for index, (name, blocks) in enumerate(synthetic_cases(seed).items()):
        result = evaluate_subject_condition(
            blocks,
            n_null=n_null,
            seed=1000 + index,
            epoch_s=0.5,
            half_window=1,
        )
        payload = _result_payload(result)
        payload["pass"] = _case_passes(name, payload)
        cases[name] = payload
    status = "PASS" if all(bool(item["pass"]) for item in cases.values()) else "FAIL"
    return {
        "gate": "r1_synthetic",
        "status": status,
        "config": config,
        "config_fingerprint": config_fingerprint(config),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--n-null", type=int, default=99)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run_r1_synthetic(seed=args.seed, n_null=args.n_null)
    write_receipt(args.output, receipt)
    for name, item in receipt["cases"].items():
        print(f"{name}: transition={item['transition_class']} state={item['state_class']} ({item['interpretation']})")
    print(receipt["status"])
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
