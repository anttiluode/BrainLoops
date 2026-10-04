# BrainLoops Phase 1 Interface Contracts

This companion freezes the cross-task type names used by `2026-10-04-brainloops-phase1.md`. Executors should treat these as part of the implementation plan; bodies may vary, but public field names and signatures should not drift between tasks.

## Shared dataclasses in `brainloops/types.py`

```python
@dataclass(frozen=True)
class ArtifactStats:
    n_epochs: int
    n_values: int
    values_clipped: int
    fraction_values_clipped: float
    epochs_over_extreme_fraction: int
    fraction_epochs_over_extreme_fraction: float

@dataclass(frozen=True)
class FeatureBatch:
    X: np.ndarray
    epoch_s: float
    feature_names: tuple[str, ...]
    artifact_stats: ArtifactStats | None = None

@dataclass(frozen=True)
class StatePartition:
    labels: np.ndarray
    centers: np.ndarray
    k: int

@dataclass(frozen=True)
class VisitSequence:
    labels: np.ndarray
    starts: np.ndarray

@dataclass(frozen=True)
class CycleSummary:
    cycle: tuple[int, int, int]
    net_flux: float
    full_rounds: int
    period_s: float | None

@dataclass(frozen=True)
class KRecurrenceResult:
    k: int
    asymmetry: float
    markov_mean: float
    markov_sd: float
    p_markov: float
    excess_z: float
    surrogate_mean: float
    surrogate_sd: float
    p_surrogate: float
    n_visits: int
    cycles: tuple[CycleSummary, ...]

RecurrenceClass = Literal[
    "NO_ROBUST_RECURRENCE",
    "LINEAR_LAG_RECURRENCE",
    "BEYOND_LINEAR_RECURRENCE",
]

@dataclass(frozen=True)
class LinearDynamicsFit:
    A: np.ndarray
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    train_r2: float

@dataclass(frozen=True)
class ModeSummary:
    eigenvalue: complex
    magnitude: float
    angle_rad: float
    decay_epochs: float | None
    period_s: float | None

@dataclass(frozen=True)
class EEGMMIDBRun:
    subject: int
    run: int
    path: Path

@dataclass(frozen=True)
class Event:
    onset_s: float
    label: str

@dataclass(frozen=True)
class EventSeries:
    events: tuple[Event, ...]

@dataclass(frozen=True)
class ClockValidationResult:
    subject: int
    run: int
    score: float
    null_scores: np.ndarray
    p_value: float
    positive_direction: bool
```

`GateReceipt` remains a JSON-serializable `dict[str, Any]` rather than a dataclass because Gate 0 and Gate 1 payloads differ. `brainloops/receipts.py` owns serialization and config fingerprints.

## Frozen function signatures

```python
# features.py
robust_scale_clip(
    X: np.ndarray,
    clip: float = 4.0,
    epoch_extreme_fraction: float = 0.10,
) -> tuple[np.ndarray, ArtifactStats]

bandpower_epochs(
    data: np.ndarray,
    sfreq: float,
    epoch_s: float = 0.5,
    bands: Mapping[str, tuple[float, float]] | None = None,
) -> FeatureBatch

# io.py
normalize_channel_name(name: str) -> str
select_region(ch_names: Sequence[str], region: str) -> list[int]
load_edf_features(
    path: str | Path,
    region: str = "All",
    epoch_s: float = 0.5,
    fs: float = 100.0,
) -> FeatureBatch

# states.py
fit_states(Z: np.ndarray, k: int, seed: int = 0) -> StatePartition
collapse_visits(labels: np.ndarray) -> VisitSequence

# circulation.py
transition_counts(seq: np.ndarray, k: int) -> np.ndarray
asymmetry_index(N: np.ndarray) -> float
top_three_cycles(
    N: np.ndarray,
    visits: VisitSequence,
    epoch_s: float,
    n: int = 5,
) -> tuple[CycleSummary, ...]
return_times(labels: np.ndarray, epoch_s: float) -> np.ndarray

# nulls.py
reversible_markov_samples(
    N: np.ndarray,
    n_steps: int,
    n_null: int,
    rng: np.random.Generator,
) -> np.ndarray
phase_surrogate(Z: np.ndarray, rng: np.random.Generator) -> np.ndarray

# dynamics.py
fit_linear_dynamics(Z: np.ndarray, ridge: float = 1e-3) -> LinearDynamicsFit
score_linear_dynamics(fit: LinearDynamicsFit, Z: np.ndarray) -> float
summarize_modes(fit: LinearDynamicsFit, epoch_s: float) -> tuple[ModeSummary, ...]

# datasets/eegmmidb.py
discover_runs(root: Path, subjects: Sequence[int] | None = None) -> list[EEGMMIDBRun]
parse_t_annotations(raw: Any) -> EventSeries
load_run(
    run: EEGMMIDBRun,
    region: str = "All",
    epoch_s: float = 0.5,
    fs: float = 100.0,
) -> tuple[FeatureBatch, EventSeries]

# receipts.py
write_receipt(path: Path, payload: Mapping[str, Any]) -> None
config_fingerprint(payload: Mapping[str, Any]) -> str

# gate0_synthetic.py
classify_recurrence(
    rows: Sequence[KRecurrenceResult],
    alpha: float = 0.05,
    required_fraction: float = 2 / 3,
) -> RecurrenceClass
run_gate0(seed: int = 1, n_null: int = 99) -> dict[str, Any]

# gate1_eegmmidb.py
clock_alignment_score(
    recurrence_periods_s: np.ndarray,
    recurrence_weights: np.ndarray,
    event_onsets_s: np.ndarray,
) -> float
run_gate1(...) -> dict[str, Any]
```

## Cross-task invariants

- `StatePartition.labels` always has one label per input epoch.
- `VisitSequence.starts` stores original epoch indices for each collapsed visit.
- `KRecurrenceResult.p_markov` and `p_surrogate` use the finite-null correction `(1 + exceedances) / (1 + n_null)`.
- Complex eigenvalues may serialize as `{real, imag}` in JSON; they must never be stringified and reparsed for calculations.
- `EventSeries` preserves exact `T0`, `T1`, `T2` labels and onset seconds; unknown labels are ignored only if explicitly documented by the EEGMMIDB adapter.
- No function in `features.py`, `states.py`, `circulation.py`, `nulls.py`, or `dynamics.py` accepts task annotations.
