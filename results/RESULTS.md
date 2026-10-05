# BrainLoops results

This file records scientific interpretation of committed receipts without rewriting the frozen implementation plan.

## Gate 0 — synthetic truth

`results/receipts/gate0-synthetic.json` is the calibration receipt for the recurrence instrument. The four preregistered synthetic classes pass.

## Gate 1A — EEGMMIDB timescale positive control

Receipt: `results/receipts/gate1-eegmmidb.json`

Observed full-dataset result:

- 109 EEGMMIDB subjects included.
- Deterministic split: 21 development subjects, 88 held-out subjects.
- 99 null samples per run.
- Held-out aggregate one-sided permutation `p = 0.01`.
- Positive direction in 73/88 held-out subjects = 82.95%.
- Receipt verdict: `PASS` under the implemented Gate-1 rule.

### What Gate 1A supports

State trajectories are fitted without event labels. Afterward, the measured return-time spectrum contains more mass near the known `T0 → T0` task-clock timescale than an occupancy-preserving state-label shuffle null. The effect direction is positive in a large majority of held-out subjects.

### What Gate 1A does not establish

The implemented null permutes the state-label timeline. That preserves state occupancy but destroys dwell structure, autocorrelation, and natural recurrence together with task alignment. The original written plan instead described circularly shifted annotation times.

The current period-only statistic uses only `T0 → T0` gaps. A common circular shift of all annotation times therefore cannot serve as its null because the gaps do not change. Gate 1A is retained as a **temporal-sensitivity/timescale positive control**, not as evidence that recurrence is specifically phase-locked to the experimental clock.

It also does not identify an anatomical loop or assign any period to hippocampal, thalamocortical, basal-ganglia, or other named circuitry.

## Gate 1B — fixed-timeline phase alignment: FAIL

Receipt: `results/receipts/gate1b-eegmmidb.json`

Gate 1B left the EEG-derived state timeline untouched and moved only the external clock. At `k = 6, 10, 20`, it measured how often successive `T0` events returned to the same unsupervised state, then compared that score with circular shifts of the annotation indices over the fixed state sequence.

Observed full-dataset result:

- 109 subjects: 21 deterministic development, 88 held out.
- 12 task runs per subject, 1,308/1,308 runs completed and 0 skipped.
- 99 circular-shift null samples per run.
- Held-out observed aggregate median score: `0.142857`.
- Held-out aggregate null median: `0.166667`.
- All 99/99 sampled aggregate null scores were at least as large as the observed aggregate score.
- Preregistered upper-tail aggregate permutation `p = 1.0`.
- Positive direction in 18/88 held-out subjects = 20.45%.
- Receipt verdict: `FAIL`.

### What Gate 1B supports

It supports a negative statement about the frozen metric: the true EEGMMIDB `T0` phase is **not** a privileged return to the same coarse unsupervised EEG state. The result is not a marginal miss; its observed direction is lower than the circular-shift null rather than higher.

That reversal is retained as a descriptive clue only. The opposite direction was not the preregistered alternative, so BrainLoops does not relabel it as a successful gate.

### What Gate 1B does not support

The failure does not erase Gate 1A's weaker timescale sensitivity. Together the receipts distinguish “structure near the known task-clock timescale” from “return to the identical coarse state at the true task phase.”

Gate 1B also does not show that the brain lacks recurrent dynamics. Its metric asks for repeated state identity, which can fail if the same experimental boundary repeatedly drives similar **transitions** from different starting states.

Artifact burden does not provide an obvious explanation for the failure in the committed receipt: all task runs completed, and correlations between clipping burden and the Gate-1B score/effect were small in the receipt analysis. The EDF annotation warnings seen during loading therefore did not manifest as skipped runs.

Under the frozen dataset ladder, Gate 1B `FAIL` keeps LEMON blocked.

## Gate 1C — repeated T0 transition geometry: PASS

Receipt analyzed: `results/receipts/gate1c-eegmmidb.json` (full 109-subject run produced with the frozen Gate-1C implementation).

Gate 1C was designed **after observing Gate 1B**. It is therefore a mechanistic follow-up on the same dataset, not an independent confirmatory test and not a rescue of Gate 1B.

The primary question changes from “does `T0` return to the same point?” to “does `T0` repeatedly produce a similar local direction of change?”

For each task run:

1. Fit an up-to-8-dimensional PCA trajectory from EEG features without annotations.
2. Convert `T0` onsets to the nearest feature epochs.
3. With half-window `w = 1`, form a symmetric transition vector
   `v_i = mean(z[t_i+1 : t_i+w+1]) - mean(z[t_i-w : t_i])`.
4. Normalize valid nonzero transition vectors and use their mean off-diagonal pairwise cosine similarity as the primary score.
5. Build the null by circularly shifting all event centers through the valid interior of the **fixed PCA trajectory**. The EEG trajectory is not shuffled or refit.
6. Aggregate runs by subject, then aggregate only the deterministic held-out subjects for the primary verdict.

Observed result:

- 109 subjects: 21 deterministic development, 88 held out.
- 12 task runs per subject, 1,308/1,308 runs completed and 0 skipped.
- 99 circular-shift null samples per run.
- Held-out observed median transition-consistency score: `0.052647`.
- Median of the 99 held-out aggregate null scores: `0.005931`.
- Aggregate null range: `0.000870` to `0.013469`; the observed median exceeds all 99 aggregate null replicates.
- One-sided aggregate permutation `p = 0.01`, the resolution floor for 99 nulls.
- Positive direction in 78/88 held-out subjects = 88.64%.
- 55/88 held-out subjects had individual one-sided `p <= 0.05`; 43/88 were at the `p = 0.01` floor.
- Development split was also directionally positive in 20/21 subjects, but it is not used for the primary verdict.
- Receipt verdict: `PASS`.

### What Gate 1C supports

Gate 1C supports **repeated transition geometry at the true `T0` phase**. The same EEG trajectory that did not repeatedly occupy one identical coarse state at `T0` nevertheless shows a reproducible local direction of change around `T0`, substantially stronger than circularly shifted control phases on the unchanged trajectory.

The cleanest joint reading of Gates 1B and 1C is therefore:

```text
same phase -> same coarse state        FAIL
same phase -> similar state change     PASS
```

That is a sharper result than the original “loop” picture. The measured object looks more like a repeated transformation through state space than a return to one fixed point.

### What Gate 1C does not establish

Gate 1C is a `post_gate1b_followup_same_dataset` analysis. The hypothesis was chosen after inspecting Gate 1B and then tested on the same EEGMMIDB subjects. The strong held-out numerical result is real for this frozen follow-up, but it is **not an independent replication**.

The result also does not by itself establish an anatomical recurrent circuit, spontaneous resting-state recurrence, a hippocampal/cortical loop, or a general history-memory mechanism. At this stage the conservative interpretation is that the known experimental boundary is associated with a repeatable local EEG state transformation that survives a fixed-timeline circular-shift null.

Gate 1B remains `FAIL`, and the original LEMON advancement criterion remains unsatisfied.

### Secondary history diagnostic: not supported

Gate 1C also records, without using it for the primary verdict, whether transition vectors are more similar after the same preceding task label (`T1/T1` or `T2/T2`) than after different preceding labels (`T1/T2`). The diagnostic is

```text
history_delta = mean cosine(same preceding task) - mean cosine(different preceding task)
```

The held-out median `history_delta` was `-0.011155`, and only 31/88 held-out subjects had positive values. There is therefore no support here for the specific coarse-history claim that matching the immediately preceding `T1`/`T2` label makes the subsequent `T0` transition more similar. This negative diagnostic is descriptive and exploratory; no confirmatory p-value was defined for it.

## Current interpretation

Across the three EEGMMIDB gates, the increasingly narrow picture is:

- Gate 1A: the unsupervised dynamics contain structure at the task-clock **timescale**.
- Gate 1B: the true task phase is **not** a privileged return to the identical coarse state.
- Gate 1C: the true task phase **is** a privileged repeated **direction of transition** through continuous PCA state space.

So the useful object emerging from BrainLoops is not yet a literal cycle with a fixed return point. It is a reproducible event-aligned state-space transformation. Whether spontaneous brain dynamics contain analogous transition motifs without an external task clock remains an open question.

## R1 — spontaneous/resting transition recurrence

Status: **implementation and synthetic calibration complete; real LEMON receipt pending**.

Frozen question:

> Can resting EEG repeatedly express the same local state-space transformation even when it does not return to the same state?

R1 is an independent-dataset follow-up motivated by EEGMMIDB Gate 1C. It does not rewrite or retroactively rescue Gate 1B.

The canonical synthetic receipt `results/receipts/r1-synthetic.json` passes at `n_null = 99` and `seed = 1`:

- iid noise: no robust transition recurrence;
- stable linear rotation: linear-lag transition recurrence;
- drifting repeated transform: transition recurrence outranks matched state recurrence, yielding a transformation-only interpretation;
- repeated state return with variable transition direction: state recurrence dominates, preventing a transformation-only label.

The real R1 analysis is not complete until raw LEMON BrainVision data are run under the frozen EC-primary / EO-replication configuration. No real LEMON result is claimed here.

The original Gate-1B dataset ladder remains frozen. R1 is a separately approved independent follow-up branch motivated by Gate 1C, not a reinterpretation of the Gate 1B failure.

## Dataset ladder

Phase 1 uses **EEGMMIDB** as a known-clock instrument test, not as the primary intrinsic-loop dataset.

Gate 1B failed its frozen phase-alignment rule, so the planned **LEMON (MPI Leipzig Mind-Brain-Body EEG)** resting-state step remains blocked under the original advancement criterion. Gate 1C is a mechanistic follow-up on EEGMMIDB and does not reopen that ladder by itself.

**CHB-MIT** is reserved for later long-duration/pathology stress testing. It will not be pooled with healthy resting EEG or used to claim normal brain-loop organization.

LEMON/Gates 2–3 and the MultipleTemporalLenses memory bridge/Gate 4 remain deferred under the original ladder.
