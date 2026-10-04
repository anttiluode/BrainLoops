from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

import mne

from .features import DEFAULT_BANDS, bandpower_epochs, robust_scale_clip
from .types import FeatureBatch

EEG_REGIONS: dict[str, tuple[str, ...]] = {
    "All": (),
    "Occipital": ("O1", "O2", "OZ", "POZ", "PO3", "PO4", "PO7", "PO8"),
    "Temporal": ("T7", "T8", "TP7", "TP8", "FT7", "FT8"),
    "Parietal": ("P1", "P2", "P3", "P4", "PZ", "CP1", "CP2"),
    "Frontal": ("FP1", "FP2", "FZ", "F1", "F2", "F3", "F4"),
    "Central": ("C1", "C2", "C3", "C4", "CZ", "FC1", "FC2"),
}


def normalize_channel_name(name: str) -> str:
    return name.strip().replace(".", "").upper()


def select_region(ch_names: Sequence[str], region: str) -> list[int]:
    if region not in EEG_REGIONS:
        raise ValueError(f"Unknown region: {region}")
    normalized = [normalize_channel_name(name) for name in ch_names]
    if region == "All":
        return list(range(len(normalized)))
    wanted = set(EEG_REGIONS[region])
    indices = [i for i, name in enumerate(normalized) if name in wanted]
    if not indices:
        raise ValueError(f"No {region} channels")
    return indices


def load_edf_features(
    path: str | Path,
    region: str = "All",
    epoch_s: float = 0.5,
    fs: float = 100.0,
) -> FeatureBatch:
    raw = mne.io.read_raw_edf(str(path), preload=True, verbose=False)
    mapping = {name: normalize_channel_name(name) for name in raw.ch_names}
    raw.rename_channels(mapping)
    indices = select_region(raw.ch_names, region)
    raw.pick([raw.ch_names[i] for i in indices])
    if fs <= 0:
        raise ValueError("fs must be positive")
    if raw.info["sfreq"] != fs:
        raw.resample(fs, verbose=False)
    channel_names = tuple(raw.ch_names)
    unscaled = bandpower_epochs(raw.get_data(), sfreq=float(raw.info["sfreq"]), epoch_s=epoch_s)
    X, stats = robust_scale_clip(unscaled.X)
    feature_names = tuple(
        f"{channel}-{band}"
        for channel in channel_names
        for band in DEFAULT_BANDS
    )
    return FeatureBatch(
        X=X,
        epoch_s=unscaled.epoch_s,
        feature_names=feature_names,
        artifact_stats=stats,
    )
