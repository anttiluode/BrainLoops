# BrainLoops Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the BrainLoops v0 measurement core, prove it on synthetic systems, and validate the instrument on EEGMMIDB's known task clock before making any resting-state claim.

**Architecture:** Shared EEG preprocessing feeds two independent measurement paths: discrete state circulation and continuous linear dynamical modes. Discrete circulation is classified against a reversible-Markov null and a multivariate phase-preserving surrogate; continuous modes are estimated with a transparent ridge/DMD-style operator. Gate 0 establishes synthetic truth, then Gate 1 tests whether unsupervised recurrence measurements recover the known EEGMMIDB task timing on held-out subjects.

**Tech Stack:** Python 3.11+, NumPy, SciPy, scikit-learn, MNE, pytest, JSON receipts; no neural-network dependency in Phase 1.

**Spec:** `docs/superpowers/specs/2026-10-04-brainloops-design.md`

## Global Constraints

- Do not infer named anatomical loops from scalp EEG recurrence.
- Keep the core scientific API headless; plots/GUI are downstream of receipts.
- Default epoch width is `0.5 s`.
- Default frequency bands are delta `1-4 Hz`, theta `4-8 Hz`, alpha `8-13 Hz`, beta `13-30 Hz`, low-gamma `30-45 Hz`.
- Robust scaling uses median/MAD; extreme individual feature values are clipped, but an epoch is not declared bad because one of hundreds of features is extreme.
- Artifact reporting must include fraction of all values clipped and count/fraction of epochs with more than `10%` extreme feature values.
- The reversible null asks whether net circulation exceeds finite-sample circulation on the same graph.
- The phase surrogate preserves multivariate linear spectra and phase lags; failing it classifies a result as linear-lag recurrence, not as “no recurrence”.
- EEGMMIDB event annotations must not participate in feature construction, PCA, clustering, or dynamical-mode fitting.
- Gate 0 must pass before Gate 1 results are accepted.
- Heavy real-data gates must be deterministic per subject/run and resumable by receipt.
- Dataset files are never committed.

## Review Focus

1. **Short or constant recordings:** preprocessing should return a clear validation error rather than NaNs or empty PCA fits. Covered in Task 1 tests.
2. **Channels missing or named inconsistently:** region selection should normalize names and fail explicitly when no requested channels exist. Covered in Task 2 tests.
3. **Sparse transition graphs:** reversible-null generation must handle zero-degree states without invalid probabilities. Covered in Task 3 tests.
4. **Near-real eigenvalues / zero-frequency modes:** continuous-mode period conversion must return `None` for non-oscillatory modes rather than huge nonsense periods. Covered in Task 4 tests.
5. **Missing or malformed EEGMMIDB annotations:** Gate 1 must skip/flag the run and never silently treat missing labels as rest. Covered in Task 6 tests.

---

## File Map

```text
pyproject.toml                       package metadata, dependencies, CLI entry point
README.md                            project question, claim boundary, reproduce Phase 1
brainloops/__init__.py               public package version
brainloops/types.py                  dataclasses shared across modules
brainloops/features.py               epoch band-power, robust scaling, artifact stats
brainloops/io.py                     EDF loading, channel normalization, region selection
brainloops/states.py                 PCA, K-means coarse-graining, visit collapse
brainloops/circulation.py            transition flux, asymmetry, motifs, return times
brainloops/nulls.py                  reversible-Markov and phase-surrogate generators
brainloops/dynamics.py               ridge linear operator and modal summaries
brainloops/datasets/eegmmidb.py      EEGMMIDB discovery and annotation parsing
brainloops/receipts.py               deterministic JSON serialization / resume helpers
brainloops/cli.py                    headless commands
experiments/gate0_synthetic.py       synthetic truth gate
experiments/gate1_eegmmidb.py        known-clock validation
results/receipts/.gitkeep            receipt destination only
tests/...                            unit and integration coverage
```

### Task 1: Package skeleton, typed results, and robust feature scaling

**Files:**
- Create: `pyproject.toml`
- Create: `brainloops/__init__.py`
- Create: `brainloops/types.py`
- Create: `brainloops/features.py`
- Create: `tests/test_features.py`

**Interfaces:**
- Produces: `ArtifactStats`, `FeatureBatch`, `robust_scale_clip(X, clip=4.0, epoch_extreme_fraction=0.10)`, `bandpower_epochs(data, sfreq, epoch_s=0.5)`.
- Later tasks consume `FeatureBatch.X` as `float64 [epochs, features]` and `FeatureBatch.epoch_s`.

- [ ] **Step 1: Write failing tests for robust scaling and artifact reporting**

```python
def test_robust_scale_reports_values_not_any_feature_epochs():
    X = np.zeros((10, 100))
    X[0, 0] = 100
    Y, stats = robust_scale_clip(X, clip=4.0, epoch_extreme_fraction=0.10)
    assert stats.n_epochs == 10
    assert stats.n_values == 1000
    assert stats.epochs_over_extreme_fraction == 0
    assert stats.values_clipped > 0
    assert np.max(np.abs(Y)) <= 4.0


def test_robust_scale_rejects_constant_or_too_short_input():
    with pytest.raises(ValueError):
        robust_scale_clip(np.zeros((1, 20)))
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pytest tests/test_features.py -q`
Expected: FAIL because `brainloops.features` does not exist.

- [ ] **Step 3: Implement dataclasses and robust scaling**

Implement in `brainloops/types.py`:
- `ArtifactStats(n_epochs: int, n_values: int, values_clipped: int, fraction_values_clipped: float, epochs_over_extreme_fraction: int, fraction_epochs_over_extreme_fraction: float)`
- `FeatureBatch(X: np.ndarray, epoch_s: float, feature_names: tuple[str, ...], artifact_stats: ArtifactStats | None = None)`

Implement in `brainloops/features.py`:
- `robust_scale_clip(X: np.ndarray, clip: float = 4.0, epoch_extreme_fraction: float = 0.10) -> tuple[np.ndarray, ArtifactStats]`
- MAD scale factor `1.4826`; zero MAD columns use scale `1.0`.

- [ ] **Step 4: Add failing tests for band-power epochs**

Assert a synthetic 10 Hz sine has higher alpha than delta power, uses exact `0.5 s` epochs, and rejects recordings shorter than two epochs.

- [ ] **Step 5: Implement `bandpower_epochs`**

Signature:
`bandpower_epochs(data: np.ndarray, sfreq: float, epoch_s: float = 0.5, bands: Mapping[str, tuple[float, float]] | None = None) -> FeatureBatch`

Use deterministic filtering/welch-style power; no learned preprocessing.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_features.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml brainloops tests/test_features.py
git commit -m "feat: add robust EEG feature pipeline"
```

### Task 2: EDF loading and channel normalization

**Files:**
- Create: `brainloops/io.py`
- Create: `tests/test_io.py`

**Interfaces:**
- Consumes: `FeatureBatch`, `bandpower_epochs`, `robust_scale_clip` from Task 1.
- Produces: `normalize_channel_name(name: str) -> str`, `select_region(ch_names, region) -> list[int]`, `load_edf_features(path, region='All', epoch_s=0.5, fs=100.0) -> FeatureBatch`.

- [ ] **Step 1: Write failing channel-normalization tests**

Cover names with whitespace, dots, case differences, and `OZ`/`POZ` style labels. Assert an unavailable requested region raises `ValueError("No <region> channels")`.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_io.py -q`
Expected: FAIL because `brainloops.io` does not exist.

- [ ] **Step 3: Implement channel normalization and region selection**

Keep the initial region sets compatible with the old probe: All, Occipital, Temporal, Parietal, Frontal, Central.

- [ ] **Step 4: Add a temporary-EDF integration test using MNE `RawArray`**

Create a few named synthetic channels, export EDF if supported by installed MNE, then assert `load_edf_features` returns finite features and normalized names. If EDF export is unavailable in CI, unit-test the loader wrapper with monkeypatched `mne.io.read_raw_edf`.

- [ ] **Step 5: Implement `load_edf_features`**

Resample to `100 Hz` by default, compute band powers, robust-scale/clip, and attach artifact statistics.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_io.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add brainloops/io.py tests/test_io.py
git commit -m "feat: add auditable EDF loading"
```

### Task 3: Discrete state circulation and both null models

**Files:**
- Create: `brainloops/states.py`
- Create: `brainloops/circulation.py`
- Create: `brainloops/nulls.py`
- Create: `tests/test_circulation.py`
- Create: `tests/test_nulls.py`

**Interfaces:**
- Produces:
  - `fit_states(Z: np.ndarray, k: int, seed: int = 0) -> StatePartition`
  - `collapse_visits(labels: np.ndarray) -> VisitSequence`
  - `transition_counts(seq: np.ndarray, k: int) -> np.ndarray`
  - `asymmetry_index(N: np.ndarray) -> float`
  - `top_three_cycles(...) -> list[CycleSummary]`
  - `return_times(labels, epoch_s) -> np.ndarray`
  - `reversible_markov_samples(N, n_steps, n_null, rng) -> np.ndarray`
  - `phase_surrogate(Z, rng) -> np.ndarray`

- [ ] **Step 1: Write failing tests for dwell collapse, flux, and return times**

Use `A A A B B C A` and assert visits become `A B C A`; verify dwell contributes nothing to antisymmetric flux; verify known return intervals in seconds.

- [ ] **Step 2: Implement state and circulation primitives**

Use K-means only for coarse-graining; state IDs are explicitly local to each `k`.

- [ ] **Step 3: Write failing reversible-null tests including sparse graphs**

Assert a symmetric two-state chain has near-zero expected asymmetry; include an unused zero-degree state and require finite output with no invalid probability row.

- [ ] **Step 4: Implement `reversible_markov_samples`**

Build transitions from `(N + N.T)/2`; sample only from occupied support while preserving array shape for the full state count.

- [ ] **Step 5: Write failing phase-surrogate tests**

For a multichannel synthetic signal, assert preserved per-dimension power spectra and preserved cross-spectral phase differences to numerical tolerance while the time-domain waveform changes.

- [ ] **Step 6: Implement `phase_surrogate`**

Apply one random phase per Fourier frequency shared across all dimensions; keep DC and Nyquist real.

- [ ] **Step 7: Run tests**

Run: `pytest tests/test_circulation.py tests/test_nulls.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add brainloops/states.py brainloops/circulation.py brainloops/nulls.py tests/test_circulation.py tests/test_nulls.py
git commit -m "feat: add circulation metrics and null models"
```

### Task 4: Continuous dynamical modes

**Files:**
- Create: `brainloops/dynamics.py`
- Create: `tests/test_dynamics.py`

**Interfaces:**
- Produces: `fit_linear_dynamics(Z, ridge=1e-3) -> LinearDynamicsFit`, `summarize_modes(fit, epoch_s) -> tuple[ModeSummary, ...]`.
- `ModeSummary` fields: `eigenvalue`, `magnitude`, `angle_rad`, `decay_epochs`, `period_s | None`.

- [ ] **Step 1: Write failing tests on planted linear systems**

Plant a damped 2-D rotation with known `r=0.95` and period `6 s` at `0.5 s` epochs; assert recovered magnitude/period within tolerance. Plant a purely real decay and assert `period_s is None`.

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_dynamics.py -q`
Expected: FAIL because `brainloops.dynamics` does not exist.

- [ ] **Step 3: Implement ridge one-step operator fit**

Signature:
`fit_linear_dynamics(Z: np.ndarray, ridge: float = 1e-3) -> LinearDynamicsFit`

Store operator `A`, eigenvalues/eigenvectors, training one-step `R²`, and provide a held-out scoring helper.

- [ ] **Step 4: Implement mode conversion**

For `lambda = r exp(i theta)`, use `period_epochs = 2*pi/abs(theta)` only when `abs(theta)` exceeds a small numerical threshold; use `decay_epochs = -1/log(r)` only for `0 < r < 1`, otherwise report `None`/infinite according to a documented rule.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_dynamics.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add brainloops/dynamics.py tests/test_dynamics.py
git commit -m "feat: add continuous recurrent mode analysis"
```

### Task 5: Gate 0 synthetic truth

**Files:**
- Create: `experiments/gate0_synthetic.py`
- Create: `tests/test_gate0.py`
- Create: `brainloops/receipts.py`
- Create: `results/receipts/.gitkeep`

**Interfaces:**
- Consumes Tasks 1–4.
- Produces: `run_gate0(seed=1, n_null=99) -> GateReceipt` and deterministic JSON at `results/receipts/gate0-synthetic.json`.

- [ ] **Step 1: Write failing integration test for the four preregistered synthetic classes**

Require these class labels:
- reversible AR noise -> `NO_ROBUST_RECURRENCE`
- rotating linear AR -> `LINEAR_LAG_RECURRENCE`
- smooth phase loop -> `LINEAR_LAG_RECURRENCE`
- variable-dwell `A -> B -> C -> A` switching -> `BEYOND_LINEAR_RECURRENCE`

- [ ] **Step 2: Implement a single `classify_recurrence` helper**

Classification rule:
- Markov null not beaten across required `k` fraction -> no robust recurrence;
- Markov beaten but phase surrogate not beaten -> linear-lag recurrence;
- both beaten -> beyond-linear recurrence.

Freeze `ks=(6, 10, 20)` and require success at `>=2/3` values for Gate 0.

- [ ] **Step 3: Implement deterministic synthetic generators and Gate 0 runner**

Use at least `2400` epochs and fixed seeds matching the self-test scale so CI has enough cycles.

- [ ] **Step 4: Implement receipt serialization/resume helpers**

`write_receipt(path, payload)` must sort keys and include seed, tested `k`, null counts, raw measurements, and verdict. Existing complete receipt for the same code-config fingerprint may be reused; incompatible config must not be silently resumed.

- [ ] **Step 5: Run Gate 0 test and full unit suite**

Run: `pytest -q`
Expected: PASS.

Run: `python experiments/gate0_synthetic.py --output results/receipts/gate0-synthetic.json`
Expected: four expected classifications and overall `PASS`.

- [ ] **Step 6: Commit**

```bash
git add experiments/gate0_synthetic.py brainloops/receipts.py tests/test_gate0.py results/receipts/.gitkeep
git commit -m "test: freeze BrainLoops synthetic truth gate"
```

### Task 6: EEGMMIDB dataset adapter and event handling

**Files:**
- Create: `brainloops/datasets/__init__.py`
- Create: `brainloops/datasets/eegmmidb.py`
- Create: `tests/test_eegmmidb.py`

**Interfaces:**
- Produces:
  - `discover_runs(root: Path, subjects: Sequence[int] | None = None) -> list[EEGMMIDBRun]`
  - `load_run(run: EEGMMIDBRun, ...) -> tuple[FeatureBatch, EventSeries]`
  - `parse_t_annotations(raw) -> EventSeries`
- `EventSeries` must preserve onset seconds and exact `T0/T1/T2` labels.

- [ ] **Step 1: Write failing filename/discovery tests**

Cover canonical `S001R03.edf` names, subject/run sorting, and skipping unrelated files.

- [ ] **Step 2: Write failing annotation tests**

Use mocked MNE annotations. Assert missing `T0/T1/T2` annotations produce an explicit `MissingAnnotationsError`; malformed event order is flagged rather than converted to rest.

- [ ] **Step 3: Implement discovery and annotation parsing**

Do not expose annotations to feature extraction. `load_run` must return features and events separately.

- [ ] **Step 4: Add an optional smoke test gated by `EEGMMIDB_ROOT`**

If the environment variable points to real data, load one run and assert finite features plus non-empty `T*` events; otherwise skip.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_eegmmidb.py -q`
Expected: PASS (real-data smoke may SKIP).

- [ ] **Step 6: Commit**

```bash
git add brainloops/datasets tests/test_eegmmidb.py
git commit -m "feat: add EEGMMIDB adapter"
```

### Task 7: Gate 1 known-clock statistic and held-out-subject protocol

**Files:**
- Create: `experiments/gate1_eegmmidb.py`
- Create: `tests/test_gate1.py`

**Interfaces:**
- Consumes EEGMMIDB `FeatureBatch` and `EventSeries`, but event labels only after unsupervised recurrence estimation.
- Produces: per-subject `ClockValidationResult` and aggregate Gate 1 receipt.

- [ ] **Step 1: Freeze the positive-control statistic in a failing synthetic test**

Use a synthetic state trajectory driven by a known alternating external clock. Estimate recurrence without labels, then score event alignment afterward. Primary statistic: power/return-mass in a predeclared period band centered on the task/rest cycle, compared against circularly shifted annotation times that preserve event spacing.

- [ ] **Step 2: Freeze development/held-out subject split logic**

Default split must be deterministic from subject ID: development subjects are used only to verify pipeline execution and choose no hyperparameters beyond the already frozen defaults; confirmatory subjects are disjoint. Store exact subject IDs in the receipt.

- [ ] **Step 3: Implement `clock_alignment_score` and annotation-shift null**

The function must accept recurrence measurements and event onsets, never raw EEG labels during state fitting.

- [ ] **Step 4: Implement Gate 1 resumable runner**

CLI arguments: `--data`, `--subjects`, `--n-null`, `--output`, `--resume`. Write one per-run record as soon as each run finishes, then aggregate.

Primary pass rule for v0: on held-out subjects, median real alignment exceeds the subject-wise annotation-shift null median with one-sided permutation `p <= 0.05`, and the effect direction is positive in at least `2/3` of held-out subjects. If available subject count is too small for the requested p-resolution, report `INSUFFICIENT_DATA` rather than pass/fail.

- [ ] **Step 5: Run synthetic Gate 1 tests**

Run: `pytest tests/test_gate1.py -q`
Expected: planted clock PASS; time-randomized control FAIL/NO_EFFECT.

- [ ] **Step 6: Run a real-data smoke when EEGMMIDB is available**

Run: `python experiments/gate1_eegmmidb.py --data <root> --subjects 1 2 --n-null 19 --output results/receipts/gate1-smoke.json`
Expected: execution completes and receipt is structurally valid; no scientific conclusion from two subjects.

- [ ] **Step 7: Commit**

```bash
git add experiments/gate1_eegmmidb.py tests/test_gate1.py
git commit -m "feat: add EEGMMIDB known-clock validation"
```

### Task 8: CLI, README, and Phase 1 verification

**Files:**
- Create: `brainloops/cli.py`
- Create: `README.md`
- Modify: `pyproject.toml`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces commands:
  - `brainloops probe recording.edf --region All`
  - `brainloops gate0 --output ...`
  - `brainloops gate1 --data ... --output ...`

- [ ] **Step 1: Write failing CLI tests**

Assert `brainloops --help` lists `probe`, `gate0`, `gate1`; bad paths return non-zero with a concise error; `probe` JSON includes artifact stats, discrete recurrence class, and continuous mode summaries.

- [ ] **Step 2: Implement the thin CLI**

The CLI should call library functions only; it must not contain scientific logic.

- [ ] **Step 3: Write README from the frozen claim boundary**

Include:
- why old self-transition “loops” were invalid;
- the three recurrence classes;
- Gate 0 and Gate 1 definitions;
- EEGMMIDB download/source instructions without redistributing data;
- explicit statement that Phase 1 does not identify hippocampal/corticothalamic/basal-ganglia loops;
- note that LEMON and Gate 4 are intentionally deferred until Gate 1 survives.

- [ ] **Step 4: Run complete verification**

Run: `python -m pip install -e '.[test]'`
Expected: install succeeds.

Run: `pytest -q`
Expected: all tests PASS; optional real-data smoke tests may SKIP when data is absent.

Run: `brainloops gate0 --output /tmp/brainloops-gate0.json`
Expected: `PASS` with all four expected synthetic classifications.

- [ ] **Step 5: Inspect the repository for accidental data/artifacts**

Run: `git status --short && find . -type f -size +5M -not -path './.git/*'`
Expected: no EEG data or unexpected large files.

- [ ] **Step 6: Commit**

```bash
git add README.md pyproject.toml brainloops/cli.py tests/test_cli.py
git commit -m "docs: publish BrainLoops phase 1 workflow"
```

## Phase 1 Completion Criterion

Phase 1 is complete only when:

1. all unit/integration tests pass;
2. Gate 0 passes exactly the four preregistered synthetic classifications;
3. the EEGMMIDB runner is deterministic and resumable;
4. a real-data Gate 1 confirmatory run has either a valid `PASS`, `FAIL`, or `INSUFFICIENT_DATA` receipt—never a narrative-only conclusion;
5. no LEMON/Gate 2 resting-state claim is started before the Gate 1 receipt is frozen.

If Gate 1 fails, the next plan is an **instrument-diagnosis plan**, not LEMON. If Gate 1 passes, write a separate `BrainLoops Phase 2` implementation plan for LEMON Gates 2–3, followed only later by a Gate 4 memory-bridge plan.
