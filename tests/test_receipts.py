from pathlib import Path

import pytest

from brainloops.receipts import write_receipt


def test_interrupted_write_preserves_previous_complete_receipt(monkeypatch, tmp_path):
    path = tmp_path / "receipt.json"
    write_receipt(path, {"status": "IN_PROGRESS", "completed": [1, 2]})
    original = path.read_bytes()
    real_write = Path.write_text

    def interrupted_write(target, text, *args, **kwargs):
        real_write(target, text[:12], *args, **kwargs)
        raise OSError("interrupted during receipt write")

    monkeypatch.setattr(Path, "write_text", interrupted_write)
    with pytest.raises(OSError, match="interrupted"):
        write_receipt(path, {"status": "PASS", "completed": [1, 2, 3]})
    assert path.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["receipt.json"]
