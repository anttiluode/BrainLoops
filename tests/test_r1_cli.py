from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import brainloops.cli as cli


def test_help_lists_existing_and_r1_commands():
    text = cli.build_parser().format_help()
    for name in ("probe", "gate0", "gate1", "gate1b", "gate1c", "r1-synthetic", "r1-lemon"):
        assert name in text


def test_r1_lemon_subjects_are_literal_strings():
    args = cli.build_parser().parse_args([
        "r1-lemon", "--data", "/tmp/lemon", "--subjects", "sub-010002", "sub-000003",
        "--output", "/tmp/out.json"
    ])
    assert args.subjects == ["sub-010002", "sub-000003"]


def test_source_tree_r1_scripts_have_help():
    root = Path(__file__).resolve().parents[1]
    for script in ("experiments/r1_synthetic.py", "experiments/r1_lemon.py"):
        result = subprocess.run([sys.executable, script, "--help"], cwd=root, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
