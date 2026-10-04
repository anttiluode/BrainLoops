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

```bash
brainloops gate1b \
  --data /path/to/eegmmidb \
  --n-null 99 \
  --output results/receipts/gate1b-eegmmidb.json \
  --resume
```

The real 109-subject receipt is now committed and Gate 1B is a **clean FAIL**. All 1,308 task runs completed; none were skipped. In the 88 held-out subjects, the observed aggregate median exact-state recurrence was `0.142857`, versus a circular-shift null median of `0.166667`. Every one of the 99 sampled aggregate null scores was at least as large as the observed score, so the preregistered upper-tail permutation value is `p = 1.0`. Only 18/88 held-out subjects (20.45%) were in the predicted positive direction.

The negative is therefore stronger than a near miss: the true `T0` phase was not a privileged return to the same coarse EEG state, and the observed direction was lower rather than higher than the null. The opposite direction was not preregistered, so it is preserved as a descriptive clue rather than relabeled as a positive gate. Gate 1B remains frozen as `FAIL`.

### Gate 1C — repeated T0 transition geometry

Gate 1B asked whether the brain returns to the **same point** at `T0`. Gate 1C asks the follow-up suggested by that failure: does `T0` repeatedly invoke a similar **local state transformation** even when its starting/ending state differs?

Gate 1C fits the continuous PCA trajectory without annotations. For each usable `T0` event it forms a symmetric transition vector

```text
v_i = mean(z after T0_i) - mean(z before T0_i)
```

with one feature epoch on each side by default. The primary score is the mean pairwise cosine similarity of the normalized `v_i` vectors. Its null circularly shifts all event centers through the valid interior of the **fixed PCA trajectory**, so the EEG dynamics remain untouched while only external clock phase changes. An event-locked repeated direction must pass the synthetic control; a smooth period-only trajectory must not automatically pass.

A secondary receipt field compares transition-vector similarity after the same preceding task label (`T1` vs `T1`, `T2` vs `T2`) with different preceding labels. That is explicitly exploratory: it cannot rescue the primary Gate-1C score.

```bash
brainloops gate1c \
  --data /path/to/eegmmidb \
  --n-null 99 \
  --output results/receipts/gate1c-eegmmidb.json \
  --resume
```

The real 109-subject Gate-1C receipt is a **PASS** under its frozen numerical rule. All 1,308 task runs completed. In the 88 held-out subjects, the median real transition-consistency score was `0.052647`, while the median of the 99 aggregate circular-shift null scores was `0.005931`; even the largest aggregate null score was only `0.013469`. The one-sided aggregate permutation value therefore hit the 99-null floor at `p = 0.01`. Positive direction held in 78/88 held-out subjects (88.64%); 55/88 subjects also had individual one-sided `p <= 0.05`.

This is the central Gate-1C conclusion: **the true `T0` phase does not return to one privileged coarse state, but it does repeatedly carry a much more consistent local direction of change than phase-shifted control times on the same untouched EEG trajectory.** In other words, Gate 1B's “same point” picture failed, while Gate 1C's “same transformation” picture survived strongly.

The secondary history diagnostic did **not** support the specific idea that the coarse preceding `T1`/`T2` label makes those transition vectors more alike. Its held-out median `history_delta` was `-0.01115` (same-preceding-task similarity minus different-preceding-task similarity), with only 31/88 held-out subjects positive. That diagnostic remains exploratory and non-primary.

Gate 1C is **not an independent confirmation**: it was designed after seeing Gate 1B and reuses EEGMMIDB. Receipts mark this scope as `post_gate1b_followup_same_dataset`. The result supports repeated transition geometry at the known experimental boundary; it does not turn Gate 1B into a pass, identify an anatomical loop, or by itself establish spontaneous resting-state recurrence.

## Dataset ladder

Phase 1 uses **EEGMMIDB** as a known-clock instrument test, not as the primary intrinsic-loop dataset.

Gate 1B failed its frozen phase-alignment rule, so the planned **LEMON (MPI Leipzig Mind-Brain-Body EEG)** resting-state step remains blocked under the original advancement criterion. Gate 1C is a mechanistic follow-up on EEGMMIDB and does not reopen that ladder by itself.

**CHB-MIT** is reserved for later long-duration/pathology stress testing. It will not be pooled with healthy resting EEG or used to claim normal brain-loop organization.

LEMON/Gates 2–3 and the MultipleTemporalLenses memory bridge/Gate 4 remain deferred under the original ladder.

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
  gate1c_eegmmidb.py
results/
  RESULTS.md
  receipts/
docs/superpowers/
```

The original design and implementation plan are frozen under `docs/superpowers/`; `results/RESULTS.md` records later corrections and observed results without rewriting that history.

## Status

- Gate 0 synthetic truth: **PASS**, implemented and frozen.
- Gate 1A EEGMMIDB timescale positive control: **PASS** on the committed 109-subject receipt (`p = 0.01`, 73/88 held-out positive), with the state-shuffle-null limitation documented.
- Gate 1B fixed-timeline phase alignment: **FAIL** on the committed 109-subject receipt (`p = 1.0`, 18/88 held-out positive; observed median `0.142857` vs null median `0.166667`).
- Gate 1C repeated T0 transition geometry: **PASS** on the 109-subject follow-up receipt (`p = 0.01`, 78/88 held-out positive; real median `0.052647` vs aggregate-null median `0.005931`). It is a post-Gate-1B same-dataset follow-up, not independent confirmation.
- Secondary Gate-1C history diagnostic: **not supported** (`history_delta = -0.01115`, 31/88 held-out positive); exploratory only.
- LEMON resting-state work: **blocked by Gate 1B FAIL** under the frozen ladder.
