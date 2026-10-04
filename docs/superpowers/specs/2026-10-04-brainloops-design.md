# BrainLoops — design specification

**Date:** 2026-10-04  
**Status:** design approved in chat; implementation not started  
**Repository:** `anttiluode/BrainLoops`

## 1. Purpose

BrainLoops asks a narrower question than the old Brain Set System:

> **What recurrent temporal structure is actually present in EEG-derived brain-state trajectories when loop periods and state counts are not chosen in advance?**

The project will measure recurrence, circulation, return times, and continuous dynamical modes from real EEG. It will explicitly separate three phenomena that were previously mixed together:

1. **Dwell / autocorrelation** — a state remains similar for a while.
2. **Linear recurrent or phase-lag structure** — rotation, travelling activity, and delayed return explainable by the multivariate linear spectrum.
3. **Higher-order circulation** — directed recurrence that survives a null preserving the linear auto/cross-spectrum.

BrainLoops will not infer an anatomical hippocampal, corticothalamic, basal-ganglia, or cortical loop merely from scalp EEG recurrence. Anatomical loops motivate the question; the primary object measured here is an **empirical temporal mode**.

A later bridge experiment will test whether empirically measured recurrent modes form a better fixed-size coordinate system for history than the hand-selected leaky states used in `MultipleTemporalLenses`.

## 2. Why a new repository

The old `brain_set_system.py` produced visually compelling “Loop” and “Hub” states, but the labels were partly built into the analysis:

- a “Loop” was a self-transition, which is largely dwell time;
- thresholds were relative to the mean across a chosen number of clusters;
- `k` was set by the analyst;
- a Sankey diagram visually emphasized backward edges without establishing biological recurrence.

The replacement probe improved this by collapsing dwell runs, measuring antisymmetric transition flux, sweeping `k`, and comparing against null models. BrainLoops turns that probe into a reproducible measurement project rather than a single visualization.

## 3. Core scientific hypothesis

A hand-built bank of leaky temporal states tends to superpose old events along similar directions. A recurrent dynamical system can instead transform past events into multiple delayed and phase-shifted coordinates.

For a linear local approximation

\[
x_{t+1}=A x_t+B u_t,
\]

complex modes of `A` naturally provide both a decay time and a rotation/return period. More generally, the historical fingerprint of a perturbation at lag `tau` can be written conceptually as

\[
H(\tau)=\frac{\partial x_t}{\partial u_{t-\tau}}.
\]

BrainLoops does **not** assume that EEG exposes `H(tau)` directly. The first goal is to measure whether stable recurrent temporal modes exist in observed EEG state trajectories. The later bridge asks whether such modes can improve the conditioning of compact temporal memory.

## 4. Dataset ladder

The project uses different datasets for different scientific jobs rather than treating one dataset as decisive.

### 4.1 EEGMMIDB — positive-control / known-clock dataset

**Source:** PhysioNet EEG Motor Movement/Imagery Dataset  
https://physionet.org/content/eegmmidb/1.0.0/

Properties relevant to BrainLoops:

- 109 volunteers;
- 64 EEG channels;
- 160 Hz sampling;
- 14 runs per subject;
- two one-minute resting baselines;
- twelve two-minute motor or motor-imagery task runs;
- EDF+ annotation channel with `T0`, `T1`, and `T2` task/rest events.

**Role:** instrument validation, not the primary intrinsic-loop dataset. The external task timing supplies a known recurrent driver. BrainLoops should demonstrate that its recurrence measurements can recover and localize temporal structure associated with this clock without using the event labels to construct the state representation.

The event labels are used only after unsupervised recurrence measurement for validation and phase-locking analysis.

### 4.2 LEMON — primary resting-state benchmark

**Source:** NEMAR `nm000179`, LEMON: MPI Leipzig Mind-Brain-Body EEG (Resting State)  
https://nemar.org/dataset/nm000179

Properties relevant to BrainLoops:

- 215 healthy participants;
- 62-channel EEG;
- approximately 16 minutes per participant;
- alternating approximately 60-second eyes-open and eyes-closed blocks;
- BIDS/NEMAR distribution.

**Role:** primary test of reproducible resting recurrent modes. Sixteen minutes is long enough to obtain many repetitions of recurrence at multi-second scales while retaining a large multi-subject replication set.

Eyes-open and eyes-closed blocks will be analysed separately for confirmatory within-condition results. Cross-block transitions may be analysed exploratorily but must not be allowed to create the primary recurrence signal.

### 4.3 CHB-MIT — long-recording/pathology stress test

**Source:** PhysioNet CHB-MIT Scalp EEG Database  
https://physionet.org/content/chbmit/1.0.0/

Properties relevant to BrainLoops:

- 22 pediatric subjects grouped into 23 cases;
- most files approximately one hour, with some two- or four-hour files;
- mostly 23 EEG channels;
- 256 Hz sampling;
- annotated seizures.

**Role:** stress-test numerical stability and long-window recurrence analysis, and test whether major pathological state changes create clearly detectable recurrence/circulation signatures.

CHB-MIT is **not** evidence for normal brain-loop organization and will not be pooled with healthy resting EEG for the primary claim.

## 5. Analysis architecture

BrainLoops will expose two independent analysis paths over the same preprocessed trajectory.

### 5.1 Shared preprocessing

Initial v0 preprocessing intentionally remains simple and auditable:

1. load EEG and standardize channel names;
2. optional channel-region selection;
3. resample to a configured rate when needed;
4. compute fixed-width epochs (initial default `0.5 s`);
5. compute log band-power features in delta, theta, alpha, beta, and low-gamma bands;
6. robustly scale each feature using median/MAD;
7. clip only extreme individual feature values;
8. reduce with PCA using a configured fixed dimension.

The artifact report must not call an epoch “bad” merely because one feature among hundreds exceeds a threshold. It will report at least:

- fraction of all feature values clipped;
- fraction/count of epochs with more than 10% of feature values beyond the clip threshold;
- retained duration after any explicit rejection.

No ICA artifact rejection is part of the preregistered v0 because it would add many decisions before the recurrence measurement itself is validated.

### 5.2 Path A — discrete state circulation

This path generalizes the current `brain_loop_probe.py`.

For each `k` in a preregistered sweep:

1. cluster PCA states with K-means;
2. collapse consecutive identical labels into **visits**, removing dwell;
3. build visit transition counts `N`;
4. define antisymmetric net flux `F = N - N.T`;
5. compute a normalized asymmetry/circulation index;
6. estimate return-time distributions;
7. identify short directed motifs as descriptive diagnostics, not anatomical circuits.

A loop-like result is not accepted from one `k`. Evidence must persist across a majority of the preregistered coarse-grainings or appear as a stable period/mode under cross-resolution matching.

State numbers are arbitrary across `k`; labels are never compared directly across resolutions.

### 5.3 Path B — continuous dynamical modes

This path avoids clustering and asks whether the latent trajectory contains stable rotating/decaying modes.

The v0 implementation will fit a regularized linear dynamical operator on training windows:

\[
z_{t+1} \approx A z_t.
\]

For each eigenvalue

\[
\lambda_j = r_j e^{i\theta_j},
\]

report:

- decay/persistence from `r_j`;
- oscillatory/return period from `theta_j` when the imaginary component is resolvable;
- held-out one-step predictive fit;
- mode stability across windows and subjects.

This is a descriptive local linear model, not a claim that the brain is globally linear.

The first implementation should prefer a small, transparent ridge/DMD-style estimator over a large neural model. More expressive state-dependent operators are downstream only if the simple model leaves reproducible residual structure.

## 6. Null models

Null choice is central because a spectral phase lag may itself be the temporal mechanism of interest.

### 6.1 Reversible Markov null

For discrete states, construct a time-reversible chain from symmetrized edge counts `(N + N.T)/2` while preserving the observed state graph and approximate edge usage.

**Question answered:** is directed circulation stronger than finite-sample circulation expected from the same graph without an arrow of time?

Passing this null supports **net circulation**, including circulation explainable by linear phase relationships.

### 6.2 Multivariate phase-randomized null

Use one random phase per frequency shared across dimensions so the surrogate preserves auto-spectra, cross-spectra, correlations, and linear phase lags while disrupting higher-order/event structure. Rerun the entire PCA/clustering pipeline for each surrogate.

**Question answered:** is there circulation beyond what the linear multivariate spectrum explains?

Failure to beat this null is **not** a failure of the temporal-lens hypothesis. It classifies the measured recurrence as **linear-lag recurrence** rather than higher-order recurrence.

### 6.3 Label/event controls

For EEGMMIDB, event annotations are withheld from state construction and model fitting. They are introduced only for the positive-control analysis: recurrence phase/return peaks should align with the known task structure more than under shuffled event timing.

For LEMON, eyes-open/eyes-closed labels define separate confirmatory analysis segments; the primary result cannot be driven by alternation between the two conditions.

## 7. Predeclared gates

### Gate 0 — synthetic instrument truth

Generate at least four synthetic families with known ground truth:

1. reversible autocorrelated noise;
2. linear rotating AR dynamics;
3. smooth forward phase loop;
4. nonlinear/discrete `A -> B -> C -> A` event switching with variable dwell.

Required classification:

- reversible noise: no robust circulation;
- rotating AR: Markov-null circulation but not beyond phase surrogate;
- smooth phase loop: linear-lag class unless higher-order structure is explicitly planted;
- event-switching loop: circulation beyond both nulls.

Gate 0 must pass before real-data claims are reported.

### Gate 1 — EEGMMIDB known-clock validation

Use task runs from multiple subjects.

Primary requirement: an unsupervised recurrence statistic must show significant phase/return structure associated with the annotated task/rest timing on held-out subjects, compared with annotation-time shuffles.

The exact statistic and subject split will be frozen in the implementation plan before the confirmatory multi-subject run.

If Gate 1 fails, silence on intrinsic loops is uninterpretable and LEMON remains exploratory.

### Gate 2 — LEMON reproducibility

Within eyes-open and eyes-closed data separately, identify recurrence modes on one portion of each recording and test them on held-out time windows.

A candidate mode must satisfy all of:

- recurrence/period estimate stable across windows;
- evidence present across more than one coarse-graining or in the continuous-mode analysis;
- replication across a preregistered fraction of subjects;
- not attributable solely to transitions between EO and EC blocks.

Group statistics will operate on period/frequency bands and mode properties, not arbitrary K-means state IDs.

### Gate 3 — linear versus higher-order recurrence

For any reproducible LEMON mode, classify evidence into:

- reversible/no directed recurrence;
- linear-lag recurrence: beats reversible Markov null but not multivariate phase surrogate;
- beyond-linear recurrence: beats both nulls.

The project reports both positive classes. It does not hide linear-lag modes merely because they fail the stricter surrogate.

### Gate 4 — compact temporal-memory bridge

Only after Gates 0–3 are frozen, construct a separate synthetic memory comparison inspired by `MultipleTemporalLenses`.

Compare under the same resident-state budget:

1. leaky exponential bank;
2. a standard delay-basis control such as Legendre/HiPPO;
3. a bank parameterized from empirically measured BrainLoops dynamical modes.

Primary measurements:

- held-out lag decoding;
- singular-value spectrum/effective rank of lag fingerprints;
- condition number over the tested lag family;
- performance at long lag under equal memory budget.

A BrainLoops-derived basis is interesting only if it improves over the standard delay-basis control, not merely over the known-weak leaky bank.

No claim that the measured EEG modes are the anatomical implementation of memory follows from a Gate 4 win.

## 8. Proposed repository structure

```text
BrainLoops/
  README.md
  pyproject.toml
  brainloops/
    io.py                 # EDF/BIDS loading and channel normalization
    features.py           # epoch features, robust scaling, artifact statistics
    states.py             # PCA, clustering, visit sequences
    circulation.py        # flux, asymmetry, motifs, return times
    dynamics.py           # ridge/DMD-style continuous modes
    nulls.py              # reversible and phase-surrogate generators
    datasets/
      eegmmidb.py          # PhysioNet adapter + annotations
      lemon.py             # BIDS/NEMAR adapter
      chbmit.py            # long-recording stress adapter
    reports.py             # JSON receipts and figure/table assembly
  experiments/
    gate0_synthetic.py
    gate1_eegmmidb.py
    gate2_lemon.py
    gate3_null_classification.py
    gate4_memory_bridge.py
  tests/
    ...
  results/
    receipts/
  docs/superpowers/
    specs/
    plans/
```

Dataset files are never committed to the repository.

## 9. Interfaces and receipts

The core scientific API should be usable without Gradio. A thin GUI may be added later for exploration, but all gates run headlessly and emit machine-readable receipts.

Expected command pattern:

```bash
brainloops probe recording.edf --region all
brainloops gate0
brainloops gate1 --data /path/to/eegmmidb
brainloops gate2 --data /path/to/lemon
```

Every confirmatory run writes JSON containing:

- git commit / code version when available;
- dataset and subject/run identifiers;
- preprocessing parameters;
- random seeds;
- all tested `k` values;
- null sample counts;
- raw per-subject/per-window measurements;
- preregistered pass/fail decision.

Plots and Markdown summaries are generated from receipts, not treated as the source of truth.

## 10. Testing strategy

Unit tests will cover:

- dwell collapse;
- transition counts and antisymmetric flux;
- reversible-null construction;
- multivariate phase surrogate spectral preservation;
- return-time calculations;
- mode period/decay conversion;
- artifact reporting;
- dataset event parsing.

Synthetic integration tests must reproduce Gate-0 class boundaries deterministically enough for CI.

Heavy real-data gates will not run in normal CI. They must support deterministic, resumable per-subject execution and aggregation so a long run can survive interruption without changing the analysis stream.

## 11. Claim boundary

BrainLoops may establish that scalp EEG state trajectories contain reproducible recurrent temporal structure at particular scales and may classify some of that structure as explainable or not explainable by linear multivariate phase relationships.

BrainLoops does **not**, from EEG recurrence alone, establish:

- a hippocampal loop period;
- a corticothalamic loop period;
- a basal-ganglia loop period;
- source localization to a particular anatomical circuit;
- that recurrence implements consciousness;
- that apical tufts are attention heads or temporal windows;
- that a temporal memory basis measured from EEG is used by biological memory.

The strongest intended bridge claim is computational:

> **If naturally measured recurrent modes form a better-conditioned fixed-size history basis than standard compact controls, recurrent temporal geometry deserves further investigation as a memory mechanism.**

## 12. Non-goals for v0

To keep the first result interpretable, v0 will not include:

- source-localized EEG inverse solutions;
- MEG/fMRI fusion;
- deep neural latent-state models;
- causal claims about named anatomical loops;
- PAC-specific analysis;
- consciousness claims;
- automatic hyperparameter search on the confirmatory datasets.

Those are downstream only if the basic recurrence measurements survive the preregistered controls.
