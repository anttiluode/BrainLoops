from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import mne
import numpy as np

from brainloops.features import ArtifactStats, FeatureBatch, bandpower_epochs, robust_scale_clip
from brainloops.io import normalize_channel_name

Condition = Literal["EO", "EC"]
_SUBJECT_RE = re.compile(r"^(sub-[A-Za-z0-9]+)$", re.IGNORECASE)


class MissingAnnotationsError(ValueError):
    pass


class MalformedAnnotationsError(ValueError):
    pass


@dataclass(frozen=True)
class LEMONSubject:
    subject_id: str
    vhdr_path: Path


@dataclass(frozen=True)
class LEMONBlock:
    condition: Condition
    start_s: float
    stop_s: float
    index: int


@dataclass(frozen=True)
class LEMONConditionFeatures:
    subject_id: str
    condition: Condition
    blocks: tuple[FeatureBatch, ...]
    artifact_stats: ArtifactStats


# Backward-compatible local names from the interrupted Task-4 draft.
@dataclass(frozen=True)
class LemonRecording:
    subject_id: str
    path: Path
    marker_path: Path
    data_path: Path


RestBlock = LEMONBlock


@dataclass(frozen=True)
class ConditionFeatureBlocks:
    condition: Condition
    blocks: tuple[np.ndarray, ...]
    artifact_stats: tuple[ArtifactStats, ...]
    epoch_s: float
    feature_names: tuple[str, ...]


def _subject_from_path(path: Path) -> str | None:
    for part in reversed(path.parts[:-1]):
        match = _SUBJECT_RE.match(part)
        if match:
            return match.group(1)
    return None


def _header_references(path: Path) -> tuple[Path, Path]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip().lower()] = value.strip()
    if "datafile" not in values or "markerfile" not in values:
        raise ValueError(f"BrainVision header lacks companion references: {path}")

    def resolve(reference: str) -> Path:
        literal = path.parent / reference
        if literal.exists():
            return literal
        return path.parent / reference.replace("\\", "/").split("/")[-1]

    return resolve(values["markerfile"]), resolve(values["datafile"])


def _choose_subject_header(subject_id: str, paths: Sequence[Path]) -> Path:
    paths = sorted(paths)
    if len(paths) == 1:
        return paths[0]
    resting = [p for p in paths if "rest" in str(p).lower()]
    if len(resting) == 1:
        return resting[0]
    candidates = resting if resting else paths
    raise ValueError(f"multiple resting BrainVision headers for {subject_id}: {candidates}")


def discover_subjects(
    root: str | Path,
    subject_ids: Sequence[str] | None = None,
) -> list[LEMONSubject]:
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(root)
    wanted = None if subject_ids is None else {str(x) for x in subject_ids}
    grouped: dict[str, list[Path]] = {}
    for path in root.rglob("*.vhdr"):
        subject_id = _subject_from_path(path)
        if subject_id is None or (wanted is not None and subject_id not in wanted):
            continue
        grouped.setdefault(subject_id, []).append(path)
    result = []
    for subject_id in sorted(grouped):
        result.append(LEMONSubject(subject_id, _choose_subject_header(subject_id, grouped[subject_id])))
    return result


def discover_recordings(
    root: str | Path,
    subjects: Sequence[str] | None = None,
) -> list[LemonRecording]:
    recordings: list[LemonRecording] = []
    for subject in discover_subjects(root, subject_ids=subjects):
        marker_path, data_path = _header_references(subject.vhdr_path)
        if not marker_path.is_file() or not data_path.is_file():
            raise ValueError(f"missing BrainVision companion file for {subject.subject_id}: {subject.vhdr_path}")
        recordings.append(LemonRecording(subject.subject_id, subject.vhdr_path, marker_path, data_path))
    return recordings


def normalize_rest_marker(description: str) -> Condition | None:
    token = str(description).strip().upper()
    if "/" in token:
        token = token.rsplit("/", 1)[-1]
    token = token.replace(" ", "")
    if token == "S200" or token == "200":
        return "EO"
    if token == "S210" or token == "210":
        return "EC"
    return None


def _duration_s(raw) -> float:
    sfreq = float(raw.info["sfreq"])
    if not np.isfinite(sfreq) or sfreq <= 0:
        raise ValueError("raw sampling frequency must be positive")
    if len(raw.times) < 1:
        raise ValueError("raw recording is empty")
    return float(raw.times[-1] + 1.0 / sfreq)


def parse_rest_blocks(annotations_or_raw, duration_s: float | None = None) -> tuple[LEMONBlock, ...]:
    if duration_s is None:
        raw = annotations_or_raw
        annotations = raw.annotations
        duration_s = _duration_s(raw)
    else:
        annotations = annotations_or_raw
    if not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("duration_s must be positive and finite")

    onsets = np.asarray(getattr(annotations, "onset", ()), dtype=float)
    descriptions = np.asarray(getattr(annotations, "description", ()), dtype=object)
    if onsets.ndim != 1 or descriptions.ndim != 1 or len(onsets) != len(descriptions):
        raise MalformedAnnotationsError("annotation onset/description arrays are malformed")

    selected: list[tuple[float, Condition]] = []
    for onset, description in zip(onsets, descriptions):
        condition = normalize_rest_marker(str(description))
        if condition is None:
            continue
        if not np.isfinite(onset) or onset < 0 or onset >= duration_s:
            raise MalformedAnnotationsError("rest marker onset is outside recording")
        selected.append((float(onset), condition))
    if len(selected) < 2:
        raise MissingAnnotationsError("recording has too few EO/EC rest markers")

    selected_onsets = np.asarray([x[0] for x in selected], dtype=float)
    if np.any(np.diff(selected_onsets) <= 0):
        raise MalformedAnnotationsError("rest marker onsets must be strictly increasing")
    conditions = [x[1] for x in selected]
    if any(a == b for a, b in zip(conditions, conditions[1:])):
        raise MalformedAnnotationsError("EO/EC rest markers must alternate")

    return tuple(
        LEMONBlock(
            condition=condition,
            start_s=start_s,
            stop_s=(selected[i + 1][0] if i + 1 < len(selected) else float(duration_s)),
            index=i,
        )
        for i, (start_s, condition) in enumerate(selected)
    )


def _unscaled_feature_blocks(raw, epoch_s: float, fs: float, min_epochs: int) -> tuple[dict[Condition, list[FeatureBatch]], tuple[str, ...]]:
    blocks = parse_rest_blocks(raw)
    by_condition: dict[Condition, list[FeatureBatch]] = {"EO": [], "EC": []}
    feature_names: tuple[str, ...] | None = None
    for block in blocks:
        start = int(round(block.start_s * fs))
        stop = int(round(block.stop_s * fs))
        if stop <= start:
            continue
        try:
            batch = bandpower_epochs(raw.get_data(start=start, stop=stop), sfreq=fs, epoch_s=epoch_s)
        except ValueError:
            continue
        if batch.X.shape[0] < min_epochs or not np.all(np.isfinite(batch.X)):
            continue
        if feature_names is None:
            feature_names = batch.feature_names
        elif batch.feature_names != feature_names:
            raise ValueError("feature names changed across physical blocks")
        by_condition[block.condition].append(batch)
    if feature_names is None:
        raise ValueError("no usable rest blocks")
    return by_condition, feature_names


def _scale_condition(
    subject_id: str,
    condition: Condition,
    batches: Sequence[FeatureBatch],
) -> LEMONConditionFeatures:
    if len(batches) < 4:
        raise ValueError(f"{condition} has fewer than four usable physical blocks")
    lengths = [batch.X.shape[0] for batch in batches]
    pooled = np.vstack([batch.X for batch in batches])
    scaled, stats = robust_scale_clip(pooled)
    if not np.all(np.isfinite(scaled)):
        raise ValueError(f"{condition} scaled features contain non-finite values")
    out: list[FeatureBatch] = []
    offset = 0
    for batch, length in zip(batches, lengths):
        out.append(
            FeatureBatch(
                X=scaled[offset : offset + length].copy(),
                epoch_s=batch.epoch_s,
                feature_names=batch.feature_names,
                artifact_stats=None,
            )
        )
        offset += length
    return LEMONConditionFeatures(subject_id, condition, tuple(out), stats)


def _prepare_raw(raw, fs: float):
    eeg_picks = mne.pick_types(raw.info, eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
    if len(eeg_picks) == 0:
        raise ValueError("no EEG channels in LEMON recording")
    raw.pick(eeg_picks)
    raw.rename_channels({name: normalize_channel_name(name) for name in raw.ch_names})
    if not np.isclose(float(raw.info["sfreq"]), fs):
        raw.resample(fs, verbose=False)
    return raw


def load_subject_conditions(
    subject: LEMONSubject,
    epoch_s: float = 0.5,
    fs: float = 100.0,
) -> dict[str, LEMONConditionFeatures]:
    if fs <= 0 or epoch_s <= 0:
        raise ValueError("fs and epoch_s must be positive")
    raw = mne.io.read_raw_brainvision(str(subject.vhdr_path), preload=True, verbose=False)
    raw = _prepare_raw(raw, fs)
    by_condition, _ = _unscaled_feature_blocks(raw, epoch_s, fs, min_epochs=43)
    result: dict[str, LEMONConditionFeatures] = {}
    for condition in ("EC", "EO"):
        if len(by_condition[condition]) < 4:
            continue
        result[condition] = _scale_condition(subject.subject_id, condition, by_condition[condition])
    if not result:
        raise ValueError("subject has no condition with at least four usable physical blocks")
    return result


def feature_blocks_from_raw(
    raw,
    epoch_s: float = 0.5,
    fs: float = 100.0,
    min_epochs: int = 43,
) -> dict[Condition, ConditionFeatureBlocks]:
    """Compatibility wrapper retained for the interrupted Task-4 tests."""
    if not np.isclose(float(raw.info["sfreq"]), fs):
        raise ValueError("feature_blocks_from_raw requires raw already resampled to requested fs")
    by_condition, names = _unscaled_feature_blocks(raw, epoch_s, fs, min_epochs=min_epochs)
    result: dict[Condition, ConditionFeatureBlocks] = {}
    for condition in ("EO", "EC"):
        scaled = _scale_condition("unknown", condition, by_condition[condition])
        result[condition] = ConditionFeatureBlocks(
            condition=condition,
            blocks=tuple(batch.X for batch in scaled.blocks),
            artifact_stats=tuple([scaled.artifact_stats] * len(scaled.blocks)),
            epoch_s=epoch_s,
            feature_names=names,
        )
    return result


def load_recording_feature_blocks(
    recording: LemonRecording,
    epoch_s: float = 0.5,
    fs: float = 100.0,
) -> dict[Condition, ConditionFeatureBlocks]:
    raw = mne.io.read_raw_brainvision(str(recording.path), preload=True, verbose=False)
    raw = _prepare_raw(raw, fs)
    return feature_blocks_from_raw(raw, epoch_s=epoch_s, fs=fs)
