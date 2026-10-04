from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import mne
import numpy as np

from brainloops.io import load_edf_features
from brainloops.types import EEGMMIDBRun, Event, EventSeries, FeatureBatch

_FILENAME = re.compile(r"^S(?P<subject>\d{3})R(?P<run>\d{2})\.edf$", re.IGNORECASE)
_ALLOWED_LABELS = frozenset({"T0", "T1", "T2"})


class MissingAnnotationsError(ValueError):
    """Raised when a task run lacks the T0/T1/T2 annotation set."""


class MalformedAnnotationsError(ValueError):
    """Raised when T annotations cannot define an ordered event clock."""


def discover_runs(root: Path, subjects: Sequence[int] | None = None) -> list[EEGMMIDBRun]:
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(root)
    wanted = None if subjects is None else {int(subject) for subject in subjects}
    runs: list[EEGMMIDBRun] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        match = _FILENAME.match(path.name)
        if match is None:
            continue
        subject = int(match.group("subject"))
        run = int(match.group("run"))
        if wanted is not None and subject not in wanted:
            continue
        runs.append(EEGMMIDBRun(subject=subject, run=run, path=path))
    runs.sort(key=lambda item: (item.subject, item.run, str(item.path)))
    return runs


def parse_t_annotations(raw: Any) -> EventSeries:
    """Return ordered T0/T1/T2 events; unrelated EDF annotations are ignored."""
    annotations = getattr(raw, "annotations", None)
    if annotations is None:
        raise MissingAnnotationsError("recording has no annotations")
    onsets = np.asarray(getattr(annotations, "onset", ()), dtype=float)
    descriptions = np.asarray(getattr(annotations, "description", ()), dtype=object)
    if onsets.ndim != 1 or descriptions.ndim != 1 or len(onsets) != len(descriptions):
        raise MalformedAnnotationsError("annotation onset/description arrays are malformed")

    selected: list[Event] = []
    for onset, description in zip(onsets, descriptions):
        label = str(description)
        if label not in _ALLOWED_LABELS:
            continue
        if not np.isfinite(onset) or onset < 0:
            raise MalformedAnnotationsError("T annotation onset is invalid")
        selected.append(Event(onset_s=float(onset), label=label))

    labels = {event.label for event in selected}
    missing = _ALLOWED_LABELS - labels
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise MissingAnnotationsError(f"recording is missing task annotations: {missing_text}")
    ordered_onsets = np.asarray([event.onset_s for event in selected], dtype=float)
    if len(ordered_onsets) > 1 and np.any(np.diff(ordered_onsets) <= 0):
        raise MalformedAnnotationsError("T annotation onsets are not strictly increasing")
    return EventSeries(events=tuple(selected))


def load_run(
    run: EEGMMIDBRun,
    region: str = "All",
    epoch_s: float = 0.5,
    fs: float = 100.0,
) -> tuple[FeatureBatch, EventSeries]:
    # Deliberately separate the unsupervised feature path from annotation parsing.
    features = load_edf_features(run.path, region=region, epoch_s=epoch_s, fs=fs)
    raw = mne.io.read_raw_edf(str(run.path), preload=False, verbose=False)
    events = parse_t_annotations(raw)
    return features, events
