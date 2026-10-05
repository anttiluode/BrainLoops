# BrainLoops R1 Resting Transition Recurrence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the frozen R1 experiment that asks whether LEMON resting EEG contains recurrent local transition geometry, independently of EEGMMIDB and without using task/event timing to locate candidate recurrence.

**Architecture:** Add one reusable continuous recurrence module that measures transition-direction recurrence and matched state recurrence over the frozen 2.0–20.0 s lag grid, then evaluates both against order-destroying and multivariate phase-preserving nulls. Add a LEMON raw-BrainVision adapter that preserves physical eyes-open/eyes-closed block boundaries, plus a resumable experiment runner that performs deterministic development/held-out splitting, EC-primary population aggregation, EO replication, and explicit outcome classification. Keep the existing Gate 1A/1B/1C code unchanged except for CLI/documentation integration.

**Tech Stack:** Python 3.11+, NumPy, SciPy, scikit-learn PCA, MNE BrainVision I/O, pytest, JSON receipts; no new runtime dependency unless a dataset-format incompatibility proves unavoidable.

**Spec:** `docs/superpowers/specs/2026-10-04-r1-spontaneous-transition-recurrence-design.md`

## Global Constraints

- Primary dataset is LEMON resting EEG; EEGMMIDB is hypothesis-generation precedent only.
- EC is the preregistered primary condition; EO is a fixed replication/robustness condition and cannot rescue EC failure.
- Subject split is `SHA256("brainloops-r1:" + subject_id)`, development iff `int(hash, 16) % 5 == 0`, held-out otherwise.
- Feature epoch width is `0.5 s`; recurrence lag grid is exactly `2.0, 2.5, ..., 20.0 s`.
- Local transition half-window is exactly `w = 1` epoch for the primary analysis.
- Subject-condition PCA dimension is `min(8, n_features, n_total_epochs - 1)`; PCA is fitted only on that subject and condition.
- Physical blocks are never concatenated for recurrence pairs. Blocks are equal-weighted with a median at each lag.
- Primary transition statistic is the max-over-lags of block-median cosine recurrence. The same max operation must be repeated inside every null replicate.
- Matched state statistic is max-over-lags of negative median squared Euclidean return distance in standardized PCA coordinates.
- Null A independently destroys temporal order within each block while preserving the relevant marginal vector/state distribution.
- Null B uses the existing multivariate shared-phase surrogate independently within each physical block and recomputes all downstream statistics.
- Canonical receipt uses `n_null = 99`; permutation p-values use `(1 + exceedances) / (1 + n_null)`.
- Population success for a statistic/null pair requires `p <= 0.05` and positive direction in at least `2/3` of held-out subjects.
- Canonical R1 result requires at least `20` usable held-out EC subjects and `n_null >= 19`; otherwise status is `INSUFFICIENT_DATA`.
- A subject-condition is usable only with at least `4` physical blocks and enough epochs per block to support the frozen 20 s lag plus transition window.
- No artifact-score threshold may be introduced after results are seen; artifact burden is reported diagnostically.
- A positive result is computational only; do not assign recurrence to named anatomical loops or claim a consciousness mechanism.
- Real LEMON data are never committed.

## Review Focus

1. **Broken or ambiguous LEMON file layouts:** recursive discovery must resolve exactly one resting BrainVision `.vhdr` recording per subject, preserve the literal `sub-*` identifier, and fail explicitly on duplicates or missing companion files. Covered in Task 4 tests.
2. **Malformed rest markers:** `S200`/`S 200` (EO) and `S210`/`S 210` (EC), plus equivalent MNE `Stimulus/...` descriptions, must normalize consistently; non-alternating or non-increasing relevant markers must raise rather than silently invent blocks. Covered in Task 4 tests.
3. **Block-boundary leakage:** no transition vector, lag pair, order-null permutation, or phase surrogate may cross a physical EC/EO block boundary. Covered in Tasks 1–2 tests.
4. **Max-lag selection bias:** every null replicate must scan the same complete lag grid and take its own maximum; no null may be evaluated only at the real-data peak. Covered in Task 2 tests.
5. **Degenerate PCA/state scaling:** zero-variance PCA components, blocks shorter than 43 epochs at 0.5 s, non-finite features, or fewer than four usable condition blocks must produce an explicit skip/validation outcome rather than NaNs. Covered in Tasks 3–5 tests.

---

## File Map

```text
brainloops/transition_recurrence.py   R1 PCA/state standardization, spectra, nulls, classification
brainloops/datasets/lemon.py          LEMON BrainVision discovery, EO/EC block parsing, feature blocks
brainloops/cli.py                     add r1-synthetic and r1-lemon commands
experiments/r1_synthetic.py           frozen R1 instrument controls and receipt
experiments/r1_lemon.py               resumable real-data runner and population aggregation
tests/test_transition_recurrence.py   core spectrum/null/classification tests
tests/test_r1_synthetic.py            five frozen synthetic controls
tests/test_lemon.py                   discovery, marker, block, feature adapter tests
tests/test_r1_lemon.py                split, aggregation, resume, receipt tests
tests/test_cli.py                     command exposure and dispatch
README.md                              R1 question, input expectations, commands, claim boundary
results/RESULTS.md                    R1 pending/result interpretation section
results/receipts/                     synthetic receipt; real receipt only after external run
```

### Task 1: Continuous transition and matched-state recurrence core

**Files:**
- Create: `brainloops/transition_recurrence.py`
- Create: `tests/test_transition_recurrence.py`

**Interfaces:**
- Produces:
  - `lag_grid(epoch_s: float = 0.5, min_s: float = 2.0, max_s: float = 20.0, step_s: float = 0.5) -> tuple[np.ndarray, np.ndarray]` returning `(lags_s, lag_epochs)`.
  - `fit_standardized_pca_blocks(blocks: Sequence[np.ndarray], pca_dim: int = 8) -> tuple[np.ndarray, ...]`.
  - `transition_vectors(Z: np.ndarray, half_window: int = 1) -> np.ndarray`.
  - `transition_recurrence_spectrum(blocks: Sequence[np.ndarray], lag_epochs: np.ndarray, half_window: int = 1) -> np.ndarray`.
  - `state_recurrence_spectrum(blocks: Sequence[np.ndarray], lag_epochs: np.ndarray) -> np.ndarray`.
  - `max_recurrence(spectrum: np.ndarray, lags_s: np.ndarray) -> tuple[float, float]` returning `(max_score, peak_lag_s)`.
- Later tasks pass one tuple of already feature-scaled blocks per subject-condition. PCA is pooled across those blocks but recurrence remains block-local.

- [ ] **Step 1: Write failing tests for the frozen lag grid and block-local transition vectors**

```python
def test_lag_grid_is_exactly_2_to_20_seconds_by_half_second():
    lags_s, lag_epochs = lag_grid(epoch_s=0.5)
    assert np.array_equal(lags_s, np.arange(2.0, 20.0 + 0.5, 0.5))
    assert np.array_equal(lag_epochs, np.arange(4, 41))


def test_transition_vectors_w1_use_pre_and_post_epoch_not_center():
    Z = np.arange(20, dtype=float).reshape(10, 2)
    V = transition_vectors(Z, half_window=1)
    assert np.array_equal(V[0], Z[2] - Z[0])
    assert V.shape[0] == len(Z) - 2
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest tests/test_transition_recurrence.py -q`
Expected: FAIL because `brainloops.transition_recurrence` does not exist.

- [ ] **Step 3: Implement lag conversion and `transition_vectors`**

Validate exact epoch-grid representability: `lag_s / epoch_s` and `step_s / epoch_s` must be integral within numerical tolerance. Reject `half_window < 1`, non-finite arrays, or blocks too short to support a vector.

- [ ] **Step 4: Add failing tests for equal-block transition recurrence and matched state recurrence**

Construct two blocks of unequal length where one long block has one recurrence value and the short block another. Assert the returned spectrum is the median of the two **block scores**, not a pair-count-weighted pooled score. Assert transition cosine uses normalized nonzero vectors and state recurrence is `-median(||z_t-z_t+lag||^2)`.

- [ ] **Step 5: Implement `transition_recurrence_spectrum` and `state_recurrence_spectrum`**

For transition recurrence, create vectors within each block first, then compare vector rows separated by `lag_epochs`; do not compare vectors from adjacent physical blocks. For state recurrence, compare standardized PCA rows at the same lag. A block that cannot support a given frozen lag is invalid for canonical R1 rather than silently omitted at that lag.

- [ ] **Step 6: Add failing PCA-standardization tests**

Assert `fit_standardized_pca_blocks`:
- fits one PCA basis to concatenated real feature blocks;
- transforms each block separately;
- returns no cross-block synthetic row;
- divides each PCA component by the real pooled component standard deviation;
- rejects a zero-variance component scale instead of producing infinities.

- [ ] **Step 7: Implement `fit_standardized_pca_blocks` and `max_recurrence`**

Use deterministic `PCA(n_components=min(8, n_features, n_total_epochs - 1), svd_solver="full")`; no random state is needed for full SVD. Break exact peak ties by choosing the smallest lag so receipt output is deterministic.

- [ ] **Step 8: Run focused tests**

Run: `pytest tests/test_transition_recurrence.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add brainloops/transition_recurrence.py tests/test_transition_recurrence.py
git commit -m "feat: add resting transition recurrence core"
```

### Task 2: Order null, phase null, and R1 outcome classification

**Files:**
- Modify: `brainloops/transition_recurrence.py`
- Modify: `tests/test_transition_recurrence.py`
- Reuse unchanged: `brainloops/nulls.py::phase_surrogate`

**Interfaces:**
- Produces:
  - `MetricNullResult(real: float, peak_lag_s: float, order_null: np.ndarray, phase_null: np.ndarray, p_order: float, p_phase: float, positive_order: bool, positive_phase: bool)` dataclass.
  - `SubjectConditionResult(transition: MetricNullResult, state: MetricNullResult, transition_class: str, state_class: str, interpretation: str, transition_spectrum: np.ndarray, state_spectrum: np.ndarray)` dataclass.
  - `evaluate_subject_condition(blocks: Sequence[np.ndarray], n_null: int, seed: int, epoch_s: float = 0.5, half_window: int = 1) -> SubjectConditionResult`.
  - `population_rule(p_value: float, positive_fraction: float, alpha: float = 0.05, required_fraction: float = 2 / 3) -> bool`.
  - `classify_recurrence_tier(order_pass: bool, phase_pass: bool) -> Literal["NO_ROBUST_RECURRENCE", "LINEAR_LAG_RECURRENCE", "BEYOND_LINEAR_RECURRENCE"]`.
  - `interpret_transition_vs_state(transition_class: str, state_class: str) -> str` using exactly the five labels frozen in the spec.

- [ ] **Step 1: Write failing order-null tests**

Create deterministic block arrays and assert each order-null replicate independently permutes rows **within each block**, preserves block length and exact row multiset, and computes its own full lag spectrum plus max. Add a regression assertion that a null scored only at the real peak would differ on a constructed example.

- [ ] **Step 2: Implement order-null generation inside `evaluate_subject_condition`**

For transition nulls, compute real transition vectors per block then independently permute vector rows within each block. For state nulls, independently permute standardized PCA rows within each block. Use one `np.random.default_rng(seed)` and deterministic draw order.

- [ ] **Step 3: Write failing phase-null tests**

Monkeypatch `phase_surrogate` with a counting surrogate and assert it is called separately for every physical block and every null replicate. Assert transition vectors and state spectra are recomputed from surrogate trajectories, not permuted from the real trajectory.

- [ ] **Step 4: Implement phase-null generation**

For each null replicate and block, call existing `phase_surrogate(Z_block, rng)`, then recompute transition/state spectra and max statistics. Never concatenate blocks before FFT.

- [ ] **Step 5: Write failing finite-null and classification tests**

Assert p-values use `(1 + count(null >= real)) / (1 + n_null)`. Freeze all class mappings and interpretation labels, including `TRANSFORMATION_ONLY_AT_ORDER_TIER`, `TRANSFORMATION_ONLY_AT_PHASE_TIER`, `JOINT_TRANSITION_AND_STATE_RECURRENCE`, `STATE_RECURRENCE_DOMINANT`, and `NO_ROBUST_RECURRENCE`.

- [ ] **Step 6: Implement p-values, positive-direction flags, and classification helpers**

`positive_*` means `real > median(null)` with a small fixed numerical tolerance, matching prior BrainLoops gates.

- [ ] **Step 7: Run focused tests**

Run: `pytest tests/test_transition_recurrence.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add brainloops/transition_recurrence.py tests/test_transition_recurrence.py
git commit -m "feat: add R1 nulls and recurrence classification"
```

### Task 3: Freeze R1 synthetic truth before touching held-out LEMON

**Files:**
- Create: `experiments/r1_synthetic.py`
- Create: `tests/test_r1_synthetic.py`

**Interfaces:**
- Consumes: `evaluate_subject_condition`, `classify_recurrence_tier`, `interpret_transition_vs_state` from Tasks 1–2.
- Produces: `run_r1_synthetic(seed: int = 1, n_null: int = 99) -> dict[str, object]`.
- Canonical receipt destination: `results/receipts/r1-synthetic.json`.

- [ ] **Step 1: Write failing tests for the four semantic synthetic cases**

Freeze deterministic generators and expected outcomes:
- `iid_noise`: transition class `NO_ROBUST_RECURRENCE`.
- `linear_rotation`: transition class `LINEAR_LAG_RECURRENCE` (order tier passes, phase tier does not).
- `drifting_repeated_transform`: transition recurrence present at least at the order tier while matched state recurrence is absent at that tier; interpretation begins `TRANSFORMATION_ONLY`.
- `state_return_variable_direction`: matched state recurrence outranks transition recurrence and must not receive a transformation-only label.

Use at least four synthetic blocks per case and the exact R1 lag grid/half-window.

- [ ] **Step 2: Implement deterministic synthetic generators and `run_r1_synthetic`**

Keep generators small enough for CI but long enough for multiple 20 s lag pairs per block. Receipt records generator parameters, exact expected/observed classes, seed, null count, code version, and config fingerprint.

- [ ] **Step 3: Write the max-statistic false-positive regression test**

Run 100 deterministic iid synthetic subjects with a test-sized `n_null = 19`; apply the same full lag scan and max statistic to real and null. Require no more than `10/100` nominal order-tier passes at `alpha=0.05`. This test is calibration only and does not replace the canonical 99-null synthetic receipt.

- [ ] **Step 4: Run synthetic tests**

Run: `pytest tests/test_r1_synthetic.py -q`
Expected: PASS.

- [ ] **Step 5: Run canonical synthetic receipt**

Run: `python experiments/r1_synthetic.py --n-null 99 --output results/receipts/r1-synthetic.json`
Expected: overall `PASS` and all frozen semantic cases satisfied.

- [ ] **Step 6: Commit**

```bash
git add experiments/r1_synthetic.py tests/test_r1_synthetic.py results/receipts/r1-synthetic.json
git commit -m "test: freeze R1 spontaneous recurrence instrument"
```

### Task 4: LEMON raw-BrainVision adapter and physical block extraction

**Files:**
- Create: `brainloops/datasets/lemon.py`
- Create: `tests/test_lemon.py`
- Reuse: `brainloops/features.py`, `brainloops/io.py`

**Dataset decision:** Canonical R1 v1 uses the public **raw BrainVision** recording (`.vhdr` + companion `.vmrk`/binary data) so the alternating physical rest-block boundaries are retained. Preprocessed condition-split `_EC.set/_EO.set` files are not accepted for the canonical R1 path because block boundaries may have been concatenated or transformed; supporting them later would require a separately frozen equivalence check.

**Interfaces:**
- Produces:
  - `LEMONSubject(subject_id: str, vhdr_path: Path)` dataclass.
  - `LEMONBlock(condition: Literal["EC", "EO"], start_s: float, stop_s: float, index: int)` dataclass.
  - `LEMONConditionFeatures(subject_id: str, condition: str, blocks: tuple[FeatureBatch, ...], artifact_stats: ArtifactStats)` dataclass.
  - `discover_subjects(root: str | Path, subject_ids: Sequence[str] | None = None) -> list[LEMONSubject]`.
  - `parse_rest_blocks(raw: Any) -> tuple[LEMONBlock, ...]`.
  - `load_subject_conditions(subject: LEMONSubject, epoch_s: float = 0.5, fs: float = 100.0) -> dict[str, LEMONConditionFeatures]`.

- [ ] **Step 1: Write failing recursive-discovery tests**

Build temporary trees representing both original-style `sub-010002/.../resting/sub-010002.vhdr` and BIDS-style `sub-010002/.../eeg/*task-resting_eeg.vhdr`. Assert literal `sub-*` IDs are preserved, results sort by ID, requested ID filtering works, and multiple candidate resting `.vhdr` files for one subject raise `ValueError` rather than selecting arbitrarily.

- [ ] **Step 2: Implement `discover_subjects`**

Require the root to exist. Candidate paths must include a `sub-*` path component and be `.vhdr`; prefer filenames/path components containing `rest`/`resting`, but still require exactly one candidate after filtering. Check the `.vhdr` file exists; MNE will validate referenced companion files at load time.

- [ ] **Step 3: Write failing marker-normalization and block tests**

Use a fake Raw annotation object. Accept descriptions whose normalized form ends in marker `200` as EO and `210` as EC, including `S200`, `S 200`, `Stimulus/S200`, and `Stimulus/S 210`. Ignore unrelated markers. Assert relevant marker onsets are finite, non-negative, strictly increasing, alternate EO/EC, and produce blocks `[marker_i, marker_{i+1})`, with the final relevant marker ending at `raw.times[-1] + 1/sfreq`.

- [ ] **Step 4: Implement `parse_rest_blocks`**

Do not infer a missing initial condition or repair duplicate/non-alternating relevant markers. Raise explicit `MissingAnnotationsError` / `MalformedAnnotationsError` equivalents local to the LEMON adapter.

- [ ] **Step 5: Write failing feature-loading tests with monkeypatched MNE Raw**

Assert loader:
- reads BrainVision once per subject;
- normalizes EEG channel names and keeps EEG channels only;
- resamples to `100 Hz`;
- extracts each physical block independently;
- computes unscaled 0.5 s bandpower blocks;
- concatenates only blocks of the **same condition** to fit one robust median/MAD scale, then splits scaled rows back to original physical blocks;
- requires each retained block to have at least `43` complete feature epochs (`20 s / 0.5 s + 2*w + 1`);
- requires at least four usable blocks for a returned condition.

- [ ] **Step 6: Implement `load_subject_conditions`**

Use `bandpower_epochs` on each block. For each condition separately, concatenate unscaled block feature matrices, call existing `robust_scale_clip` once, then split the scaled matrix back by block lengths into `FeatureBatch` objects sharing epoch width and feature names. Store the pooled condition artifact stats on `LEMONConditionFeatures`. Do not discard a condition because artifact fractions are high; discard only invalid/too-short blocks and fail the condition if fewer than four remain.

- [ ] **Step 7: Add optional real-data smoke test**

`@pytest.mark.skipif("LEMON_ROOT" not in os.environ, ...)`: discover the first subject, load conditions, and assert EC and EO each have at least four finite blocks with identical feature width.

- [ ] **Step 8: Run adapter tests**

Run: `pytest tests/test_lemon.py -q`
Expected: PASS (real smoke may skip).

- [ ] **Step 9: Commit**

```bash
git add brainloops/datasets/lemon.py tests/test_lemon.py
git commit -m "feat: add auditable LEMON resting EEG adapter"
```

### Task 5: R1 subject split, resumable runner, and population verdict

**Files:**
- Create: `experiments/r1_lemon.py`
- Create: `tests/test_r1_lemon.py`

**Interfaces:**
- Consumes: `discover_subjects`, `load_subject_conditions`, `fit_standardized_pca_blocks`, `evaluate_subject_condition`, existing `write_receipt`, `config_fingerprint`.
- Produces:
  - `is_development_subject(subject_id: str) -> bool` using the exact SHA-256 rule.
  - `aggregate_population(subject_rows: Sequence[dict], metric: Literal["transition", "state"], null_kind: Literal["order", "phase"], n_null: int) -> dict[str, object]`.
  - `run_r1(data: str | Path, subject_ids: Sequence[str] | None = None, n_null: int = 99, output: str | Path | None = None, resume: bool = False, seed: int = 0) -> dict[str, object]`.

- [ ] **Step 1: Write failing deterministic split tests**

Hard-code several literal `sub-*` identifiers and expected booleans computed from `SHA256("brainloops-r1:" + subject_id) % 5`. Assert leading zeroes are part of the identity and that file ordering cannot change the split.

- [ ] **Step 2: Implement `is_development_subject`**

Use UTF-8 encoding of the exact concatenated string; no numeric conversion of the subject ID.

- [ ] **Step 3: Write failing population aggregation tests**

Use synthetic subject rows with known real/order-null/phase-null arrays. Assert:
- subject real values are aggregated by median;
- null replicate `j` is aggregated across subjects by median of each subject's `j`th null value;
- finite-null p-value and positive-direction fraction are correct;
- population pass requires both `p <= 0.05` and `>= 2/3` positive;
- `<20` held-out EC subjects or `n_null < 19` yields `INSUFFICIENT_DATA` for the canonical primary verdict.

- [ ] **Step 4: Implement `aggregate_population` and class mapping**

Transition and state each get order-tier and phase-tier population tests. Convert those four booleans into frozen recurrence classes and the five-label transition-vs-state interpretation using Task 2 helpers.

- [ ] **Step 5: Write failing runner/resume tests with a fake LEMON adapter**

Monkeypatch discovery and loading for at least 25 synthetic subjects so both development and held-out paths exist. Assert the receipt contains:
- `gate = "r1_lemon_resting_transition_recurrence"`;
- exact config and fingerprint before results;
- `development_subjects` and `heldout_subjects` lists;
- per-subject EC and EO rows;
- EC primary status (`PASS_LINEAR`, `PASS_BEYOND_LINEAR`, `FAIL`, or `INSUFFICIENT_DATA`);
- transition/state classes and interpretation label;
- EO replication result stored separately and never used to change EC status;
- artifact statistics and usable block counts;
- resumable completed subject-condition rows are not reloaded.

- [ ] **Step 6: Implement `run_r1`**

Processing order is sorted subject ID, then EC before EO. Seed each subject-condition deterministically from the top-level seed plus a stable hash of `subject_id + condition`; do not use Python's randomized `hash()`. Write an `IN_PROGRESS` receipt after each completed subject-condition so long real-data runs survive interruption.

For each subject-condition:
1. load feature blocks from the adapter;
2. fit/standardize one PCA basis across that condition's real blocks;
3. evaluate transition/state recurrence and both nulls;
4. append per-subject result including real spectra, peak lags, null max arrays, p-values, classes, artifact stats, and block counts.

After all available rows, compute EC held-out population verdict first, then EO replication with the same rules. No exploratory alternative window/lag/PCA setting is run in this canonical function.

- [ ] **Step 7: Add artifact-diagnostic tests**

Assert the final receipt reports Pearson and Spearman correlation (when defined) between held-out subject artifact `fraction_values_clipped` and transition effect `M_v_real - median(order_null)` as descriptive fields only. Constant artifact/effect arrays return `None` rather than warnings/NaNs.

- [ ] **Step 8: Run runner tests**

Run: `pytest tests/test_r1_lemon.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add experiments/r1_lemon.py tests/test_r1_lemon.py
git commit -m "feat: add resumable LEMON R1 gate"
```

### Task 6: CLI, packaging visibility, and source-tree commands

**Files:**
- Modify: `brainloops/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_packaging.py` only if wheel-content assertions need explicit new module coverage

**Interfaces:**
- Adds commands:
  - `brainloops r1-synthetic --n-null 99 --output results/receipts/r1-synthetic.json --seed 1`
  - `brainloops r1-lemon --data PATH --n-null 99 --output results/receipts/r1-lemon.json --resume [--subjects sub-010002 ...] [--seed 0]`

- [ ] **Step 1: Write failing CLI-help tests**

Update the existing help test to require `r1-synthetic` and `r1-lemon` in addition to all existing commands. Assert `r1-lemon --subjects` accepts literal string subject IDs rather than integers.

- [ ] **Step 2: Implement parser entries and dispatch**

Follow the existing lazy-import pattern so basic `brainloops --help` does not load MNE dataset code unnecessarily. Return code `0` for scientific statuses `PASS_LINEAR`, `PASS_BEYOND_LINEAR`, `FAIL`, and `INSUFFICIENT_DATA`; parser/data errors remain nonzero.

- [ ] **Step 3: Add source-tree help smoke tests**

Run both `python experiments/r1_synthetic.py --help` and `python experiments/r1_lemon.py --help` from repository root and require return code 0.

- [ ] **Step 4: Run CLI and packaging tests**

Run: `pytest tests/test_cli.py tests/test_packaging.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add brainloops/cli.py tests/test_cli.py tests/test_packaging.py experiments/r1_synthetic.py experiments/r1_lemon.py
git commit -m "feat: expose R1 resting recurrence commands"
```

### Task 7: Documentation, synthetic receipt, and final verification

**Files:**
- Modify: `README.md`
- Modify: `results/RESULTS.md`
- Create/update: `results/receipts/r1-synthetic.json`
- Do **not** fabricate `results/receipts/r1-lemon.json` without real LEMON execution.

**Interfaces:**
- Documents canonical raw LEMON input expectations, fixed EC/EO interpretation, commands, outcome classes, and claim boundary.

- [ ] **Step 1: Update README with an R1 section**

State that R1 is a new independent-dataset branch motivated by Gate 1C, not a rewrite of the original frozen Gate-1B ladder. Document why canonical R1 v1 uses raw BrainVision block markers, the exact commands, the three recurrence classes, and the transformation-only vs joint interpretation.

- [ ] **Step 2: Update `results/RESULTS.md` with R1 status = implementation/calibration only**

Record the frozen question and synthetic calibration status. Until real LEMON is run, explicitly say `real LEMON receipt pending`; do not speculate about the result.

- [ ] **Step 3: Run the complete test suite fresh**

Run: `python -m pytest -q`
Expected: all tests pass; only optional real-data smoke tests may skip when `EEGMMIDB_ROOT` / `LEMON_ROOT` are unset.

- [ ] **Step 4: Run canonical R1 synthetic gate fresh**

Run: `python experiments/r1_synthetic.py --n-null 99 --seed 1 --output /tmp/r1-synthetic-final.json`
Expected: `PASS`. Compare config/result fields with committed `results/receipts/r1-synthetic.json`; regenerate committed receipt only if code/config changed deliberately during implementation.

- [ ] **Step 5: Verify build/install surface**

Run:
```bash
python -m build --wheel
python -m pip install --target /tmp/brainloops-r1-install dist/*.whl
PYTHONPATH=/tmp/brainloops-r1-install python -m brainloops.cli --help
```
Expected: wheel builds; installed help includes `r1-synthetic` and `r1-lemon`; `brainloops`, `experiments.r1_synthetic`, and `experiments.r1_lemon` import from the clean target.

- [ ] **Step 6: Verify no raw data or oversized accidental artifacts**

Run: `git status --short` and inspect tracked file sizes. No raw `.vhdr`, `.vmrk`, EEG binary, `.set`, `.fdt`, archive, or subject data may be committed.

- [ ] **Step 7: Commit docs/receipts**

```bash
git add README.md results/RESULTS.md results/receipts/r1-synthetic.json
git commit -m "docs: publish R1 resting recurrence workflow"
```

- [ ] **Step 8: Stop before real held-out interpretation if LEMON data are unavailable**

Implementation completion means the frozen synthetic gate, adapter, CLI, resumability, and full suite are verified. Scientific R1 completion additionally requires a real canonical LEMON run. If local LEMON data are unavailable in the implementation environment, report the exact command and leave the real receipt pending rather than substituting another dataset.

Canonical real command:

```bash
brainloops r1-lemon \
  --data /path/to/lemon-raw \
  --n-null 99 \
  --output results/receipts/r1-lemon.json \
  --resume
```

On Windows:

```bat
brainloops r1-lemon --data "E:\path\to\lemon-raw" --n-null 99 --output results\receipts\r1-lemon.json --resume
```
