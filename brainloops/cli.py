from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .receipts import write_receipt

try:  # Existing full repository provides this; local execution scratch may not.
    from .probe import probe_edf
except ImportError:  # pragma: no cover - exercised only by stripped local scratch
    probe_edf = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brainloops", description="Measure recurrent temporal structure in EEG")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="probe one EDF recording")
    probe.add_argument("recording", type=Path)
    probe.add_argument("--region", default="All")
    probe.add_argument("--n-null", type=int, default=19)
    probe.add_argument("--seed", type=int, default=0)

    gate0 = sub.add_parser("gate0", help="run the synthetic truth gate")
    gate0.add_argument("--output", type=Path, required=True)
    gate0.add_argument("--n-null", type=int, default=99)
    gate0.add_argument("--seed", type=int, default=1)

    for name, help_text in (
        ("gate1", "run the EEGMMIDB timescale positive control"),
        ("gate1b", "test EEGMMIDB phase alignment with circular annotation shifts"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--data", type=Path, required=True)
        p.add_argument("--subjects", type=int, nargs="*")
        p.add_argument("--n-null", type=int, default=99)
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--resume", action="store_true")
        p.add_argument("--seed", type=int, default=0)

    gate1c = sub.add_parser("gate1c", help="test repeated T0 transition geometry against circular clock shifts")
    gate1c.add_argument("--data", type=Path, required=True)
    gate1c.add_argument("--subjects", type=int, nargs="*")
    gate1c.add_argument("--n-null", type=int, default=99)
    gate1c.add_argument("--output", type=Path, required=True)
    gate1c.add_argument("--resume", action="store_true")
    gate1c.add_argument("--seed", type=int, default=0)
    gate1c.add_argument("--half-window", type=int, default=1)

    r1s = sub.add_parser("r1-synthetic", help="run the frozen R1 spontaneous-recurrence synthetic gate")
    r1s.add_argument("--n-null", type=int, default=99)
    r1s.add_argument("--output", type=Path, required=True)
    r1s.add_argument("--seed", type=int, default=1)

    r1 = sub.add_parser("r1-lemon", help="run R1 on LEMON raw resting BrainVision EEG")
    r1.add_argument("--data", type=Path, required=True)
    r1.add_argument("--subjects", nargs="*")
    r1.add_argument("--n-null", type=int, default=99)
    r1.add_argument("--output", type=Path, required=True)
    r1.add_argument("--resume", action="store_true")
    r1.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "probe":
            if not args.recording.is_file():
                raise FileNotFoundError(args.recording)
            fn = probe_edf
            if fn is None:
                from .probe import probe_edf as fn
            payload = fn(args.recording, region=args.region, n_null=args.n_null, seed=args.seed)
            print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
            return 0
        if args.command == "gate0":
            from experiments.gate0_synthetic import run_gate0
            payload = run_gate0(seed=args.seed, n_null=args.n_null)
            write_receipt(args.output, payload)
            print(payload["status"])
            return 0 if payload["status"] == "PASS" else 1
        if args.command == "gate1":
            from experiments.gate1_eegmmidb import run_gate1
            payload = run_gate1(data=args.data, subjects=args.subjects, n_null=args.n_null, output=args.output, resume=args.resume, seed=args.seed)
            print(payload["status"])
            return 0 if payload["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1
        if args.command == "gate1b":
            from experiments.gate1b_eegmmidb import run_gate1b
            payload = run_gate1b(data=args.data, subjects=args.subjects, n_null=args.n_null, output=args.output, resume=args.resume, seed=args.seed)
            print(payload["status"])
            return 0 if payload["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1
        if args.command == "gate1c":
            from experiments.gate1c_eegmmidb import run_gate1c
            payload = run_gate1c(data=args.data, subjects=args.subjects, n_null=args.n_null, output=args.output, resume=args.resume, seed=args.seed, half_window=args.half_window)
            print(payload["status"])
            return 0 if payload["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1
        if args.command == "r1-synthetic":
            from experiments.r1_synthetic import run_r1_synthetic
            payload = run_r1_synthetic(seed=args.seed, n_null=args.n_null)
            write_receipt(args.output, payload)
            print(payload["status"])
            return 0 if payload["status"] == "PASS" else 1
        if args.command == "r1-lemon":
            from experiments.r1_lemon import run_r1
            payload = run_r1(data=args.data, subject_ids=args.subjects, n_null=args.n_null, output=args.output, resume=args.resume, seed=args.seed)
            print(payload["status"])
            return 0 if payload["status"] in {"PASS_LINEAR", "PASS_BEYOND_LINEAR", "FAIL", "INSUFFICIENT_DATA"} else 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    raise RuntimeError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
