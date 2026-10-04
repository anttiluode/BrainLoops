# BrainLoops

BrainLoops asks a deliberately narrow question:

> **What recurrent temporal structure is actually present in EEG-derived state trajectories when loop periods and state counts are not chosen in advance?**

It grew out of an older `brain_set_system.py` visualization that called long self-transitions “loops.” That was not enough: band-power trajectories are autocorrelated, so dwell appears even in null data, the number of states was chosen by us, and Sankey wrap-around arcs made ordinary backward transitions look like circuits.

BrainLoops replaces that picture with measurements and explicit nulls.

## What counts as recurrence here

The project keeps three outcomes separate:

1. **No robust recurrence** — directed circulation does not reliably beat a reversible Markov chain built on the same state graph.
2. **Linear-lag recurrence** — circulation beats the reversible null but not a multivariate phase-randomized surrogate that preserves auto/cross-spectra and linear phase lags.
3. **Beyond-linear recurrence** — circulation beats both nulls, so the observed arrow-of-time structure is not explained by those linear lagged spectra alone.

The second class is a positive result, not a failed third class. A linear recurrent system can create useful delayed/rotating temporal coordinates.

BrainLoops also fits a small ridge/DMD-style linear operator directly to the PCA trajectory and reports its decaying/rotating modes. The discrete state path and continuous mode path are intentionally independent views of the same recording.

## Claim boundary

Scalp EEG recurrence does **not** identify an anatomical loop. BrainLoops does not claim that a measured period belongs to the hippocampus, a cortico-thalamo-cortical circuit, basal ganglia, or any other named pathway. It also does not claim that recurrence explains consciousness or that apical tufts are transformer attention heads.

The first useful claim is computational: can reproducible recurrent temporal modes be measured at all, and can they later form a better-conditioned fixed-size history basis than hand-picked leaky memories?

## Phase 1 gates

### Gate 0 — synthetic truth

Four planted systems freeze what the instrument must distinguish:

| synthetic system | required class |
|---|---|
| reversible autocorrelated noise | no robust recurrence |
| damped linear rotation | linear-lag recurrence |
| smooth fundamental phase rotation | linear-lag recurrence |
| variable-dwell A→B→C→A switching | beyond-linear recurrence |

The smooth control uses only fundamental sine/cosine quadrature. A harmonic such as `cos(2*phase)` introduces cross-frequency phase coupling that a spectrum-preserving surrogate is supposed to destroy, so it is not a clean linear-lag control at high null resolution.

Run:

```bash
brainloops gate0 --output results/receipts/gate0-synthetic.json
```

The committed Phase-1 Gate-0 receipt uses 99 null samples and passes all four frozen classes.

### Gate 1A — EEGMMIDB timescale positive control

Before asking about spontaneous resting recurrence, BrainLoops must recover a temporal driver that is known to exist.

The [PhysioNet EEG Motor Movement/Imagery Dataset](https://physionet.org/content/eegmmidb/1.0.0/) contains 64-channel, 160 Hz EEG from 109 volunteers. Runs 3–14 alternate task and rest epochs and include EDF+ annotations `T0` (rest), `T1`, and `T2` (task conditions).

BrainLoops constructs PCA/K-means state trajectories **without annotations**. Only afterward Gate 1A asks whether the measured state return-time spectrum carries excess mass at successive `T0 → T0` intervals (the full rest/task cycle). Its implemented null permutes the unsupervised state-label timeline while preserving state occupancy, then recomputes return periods. Labels therefore validate the clock; they never construct the states.

```bash
brainloops gate1 \
  --data /path/to/eegmmidb \
  --n-null 99 \
  --output results/receipts/gate1-eegmmidb.json \
  --resume
```

The committed full-dataset receipt contains all 109 subjects, with 21 deterministic development subjects and 88 held-out subjects. Gate 1A passes its implemented rule with aggregate `p = 0.01`; 73/88 held-out subjects (82.95%) are in the positive direction.

That result is useful, but its scope is narrower than the original written Gate-1 plan. The frozen plan described circular annotation shifts; the implemented null instead shuffles the state-label timeline, which destroys temporal autocorrelation as well as task alignment. Also, the period-only score depends on `T0 → T0` gaps, so a common circular shift of all annotations would leave that statistic unchanged. BrainLoops therefore preserves the result as **Gate 1A: a temporal-sensitivity/timescale positive control**, not as the final phase-alignment confirmation.

### Gate 1B — fixed-timeline phase alignment

Gate 1B keeps the EEG-derived state timeline completely fixed and moves only the external clock.

For each unsupervised state coarse-graining (`k = 6, 10, 20`), it samples the state at successive `T0` onsets and measures how often consecutive `T0` events return to the same state. The null circularly shifts the annotation indices across the fixed state timeline. This preserves state occupancy, dwell, autocorrelation, recurrence, and the exact `T0` spacing; it changes only which phase of the EEG trajectory is called `T0`.

A deliberately important synthetic control is included: a trajectory that is perfectly periodic at the correct period but has no special `T0` phase must **not** automatically pass Gate 1B. An event-locked anchor does pass.

Run:

```bash
brainloops gate1b \
  --data /path/to/eegmmidb \
  --n-null 99 \
  --output results/receipts/gate1b-eegmmidb.json \
  --resume
```

Gate 1B uses the same held-out-subject rule as Gate 1A: aggregate one-sided permutation `p <= 0.05` and positive direction in at least `2/3` of held-out subjects. A real Gate-1B receipt is required before BrainLoops advances to resting-state claims.

## Dataset ladder

Phase 1 uses **EEGMMIDB** as a known-clock instrument test, not as the primary intrinsic-loop dataset.

If Gate 1B passes, the next planned dataset is **LEMON (MPI Leipzig Mind-Brain-Body EEG)**: healthy resting EEG with recordings long enough to test multi-second recurrence across many subjects. Eyes-open and eyes-closed blocks will be handled separately so the block alternation cannot create the primary result.

**CHB-MIT** is reserved for later long-duration/pathology stress testing. It will not be pooled with healthy resting EEG or used to claim normal brain-loop organization.

LEMON/Gates 2–3 and the MultipleTemporalLenses memory bridge/Gate 4 are intentionally deferred until Gate 1B survives.

## Probe one EDF

```bash
brainloops probe recording.edf --region All
```

The command emits JSON containing:

- artifact statistics from median/MAD scaling and per-value clipping;
- discrete recurrence results across `k = 6, 10, 14, 20` with both nulls;
- a recurrence class;
- continuous linear mode summaries with magnitude, decay scale, and oscillatory period when defined.

The artifact guard reports the fraction of **values** clipped and the fraction of epochs with more than 10% extreme features. It does not call an epoch bad merely because one of hundreds of features crossed the threshold.

## Install and test

Python 3.11+:

```bash
python -m pip install -e '.[test]'
pytest -q
brainloops gate0 --output /tmp/brainloops-gate0.json
```

Real EEG data are never committed to this repository. An optional `EEGMMIDB_ROOT` environment variable enables the real-data adapter smoke test during `pytest`; without it that one test skips.

## Repository layout

```text
brainloops/
  features.py       band-power epochs, robust scaling, artifact statistics
  io.py             EDF loading and channel normalization
  states.py         PCA-facing K-means state partitions and dwell collapse
  circulation.py    antisymmetric flux, motifs, return times
  nulls.py          reversible Markov and phase-preserving surrogates
  dynamics.py       ridge/DMD-style continuous modes
  probe.py          headless combined probe
  datasets/
    eegmmidb.py     EEGMMIDB discovery + T0/T1/T2 parsing
experiments/
  gate0_synthetic.py
  gate1_eegmmidb.py
  gate1b_eegmmidb.py
results/
  RESULTS.md
  receipts/
docs/superpowers/
```

The original design and implementation plan are frozen under `docs/superpowers/`; `results/RESULTS.md` records the Gate-1A correction rather than rewriting that history.

## Status

- Gate 0 synthetic truth: **PASS**, implemented and frozen.
- Gate 1A EEGMMIDB timescale positive control: **PASS** on the committed 109-subject receipt (`p = 0.01`, 73/88 held-out positive), with the state-shuffle-null limitation documented.
- Gate 1B fixed-timeline phase alignment: implemented with synthetic positive and period-only negative controls; **real EEGMMIDB receipt pending**.
- LEMON resting-state work: deferred until Gate 1B survives.
