from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_project_builds_wheel_with_r1_modules(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "--wheel-dir", str(tmp_path)],
        cwd=repo, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    wheels = list(tmp_path.glob("brainloops-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as zf:
        names = set(zf.namelist())
    assert "brainloops/transition_recurrence.py" in names
    assert "brainloops/datasets/lemon.py" in names
    assert "experiments/r1_synthetic.py" in names
    assert "experiments/r1_lemon.py" in names
