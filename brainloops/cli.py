from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .probe import probe_edf
from .receipts import write_receipt


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

    gate1 = sub.add_parser("gate1", help="run the EEGMMIDB timescale positive control")
    gate1.add_argument("--data", type=Path, required=True)
    gate1.add_argument("--subjects", type=int, nargs="*")
    gate1.add_argument("--n-null", type=int, default=99)
    gate1.add_argument("--output", type=Path, required=True)
    gate1.add_argument("--resume", action="store_true")
    gate1.add_argument("--seed", type=int, default=0)

    gate1b = sub.add_parser("gate1b", help="test EEGMMIDB phase alignment with circular annotation shifts")
    gate1b.add_argument("--data", type=Path, required=True)
    gate1b.add_argument("--subjects", type=int, nargs="*")
    gate1b.add_argument("--n-null", type=int, default=99)
    gate1b.add_argument("--output", type=Path, required=True)
    gate1b.add_argument("--resume", action="store_true")
    gate1b.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "probe":
            if not args.recording.is_file():
                raise FileNotFoundError(args.recording)
            payload = probe_edf(args.recording, region=args.region, n_null=args.n_null, seed=args.seed)
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

            payload = run_gate1(
                data=args.data,
                subjects=args.subjects,
                n_null=args.n_null,
                output=args.output,
                resume=args.resume,
                seed=args.seed,
            )
            print(payload["status"])
            return 0 if payload["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1
        if args.command == "gate1b":
            from experiments.gate1b_eegmmidb import run_gate1b

            payload = run_gate1b(
                data=args.data,
                subjects=args.subjects,
                n_null=args.n_null,
                output=args.output,
                resume=args.resume,
                seed=args.seed,
            )
            print(payload["status"])
            return 0 if payload["status"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"} else 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    raise RuntimeError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
