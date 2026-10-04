from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_project_builds_wheel_from_repo_root(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(tmp_path),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert list(tmp_path.glob("brainloops-*.whl"))
