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

### Gate 1 — EEGMMIDB known-clock positive control

Before asking about spontaneous resting recurrence, BrainLoops must recover a temporal driver that is known to exist.

The [PhysioNet EEG Motor Movement/Imagery Dataset](https://physionet.org/content/eegmmidb/1.0.0/) contains 64-channel, 160 Hz EEG from 109 volunteers. Runs 3–14 alternate task and rest epochs and include EDF+ annotations `T0` (rest), `T1`, and `T2` (task conditions).

BrainLoops constructs PCA/K-means state trajectories **without annotations**. Only afterward it asks whether the measured state return-time spectrum carries excess mass at successive `T0 → T0` intervals (the full rest/task cycle). Its positive-control null permutes the unsupervised state-label timeline while preserving state occupancy, then recomputes return periods. Labels therefore validate the clock; they never construct the states.

```bash
brainloops gate1 \
  --data /path/to/eegmmidb \
  --n-null 99 \
  --output results/receipts/gate1-eegmmidb.json \
  --resume
```

Gate 1 requires at least three held-out subjects and null resolution sufficient for `p <= 0.05`. Otherwise it reports `INSUFFICIENT_DATA`. A real confirmatory Gate-1 receipt is required before BrainLoops moves on to healthy resting-state claims.

## Dataset ladder

Phase 1 uses **EEGMMIDB** as a known-clock instrument test, not as the primary intrinsic-loop dataset.

If Gate 1 passes, the next planned dataset is **LEMON (MPI Leipzig Mind-Brain-Body EEG)**: healthy resting EEG with recordings long enough to test multi-second recurrence across many subjects. Eyes-open and eyes-closed blocks will be handled separately so the block alternation cannot create the primary result.

**CHB-MIT** is reserved for later long-duration/pathology stress testing. It will not be pooled with healthy resting EEG or used to claim normal brain-loop organization.

LEMON/Gates 2–3 and the MultipleTemporalLenses memory bridge/Gate 4 are intentionally deferred until Gate 1 survives.

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
results/receipts/
docs/superpowers/
```

The design and implementation plan are frozen under `docs/superpowers/`.

## Status

- Gate 0 synthetic truth: implemented and frozen.
- Gate 1 EEGMMIDB runner: implemented, deterministic, and resumable.
- Real Gate 1 confirmatory verdict: **not supplied by the repository itself**; run it on the dataset and preserve the receipt before advancing to LEMON.
