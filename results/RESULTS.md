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

Gate 1B also does not show that the brain lacks recurrent dynamics. Its metric asks for repeated state identity, which can fail if the same experimental boundary repeatedly drives similar **transitions** from different history-dependent starting states.

Artifact burden does not provide an obvious explanation for the failure in the committed receipt: all task runs completed, and correlations between clipping burden and the Gate-1B score/effect were small in the receipt analysis. The EDF annotation warnings seen during loading therefore did not manifest as skipped runs.

Under the frozen dataset ladder, Gate 1B `FAIL` keeps LEMON blocked.

## Gate 1C — repeated T0 transition geometry

Status: implementation and synthetic tests complete; real EEGMMIDB receipt pending.

Gate 1C was designed **after observing Gate 1B**. It is therefore a mechanistic follow-up on the same dataset, not an independent confirmatory test and not a rescue of Gate 1B.

The primary question changes from “does `T0` return to the same point?” to “does `T0` repeatedly produce a similar local direction of change?”

For each task run:

1. Fit an up-to-8-dimensional PCA trajectory from EEG features without annotations.
2. Convert `T0` onsets to the nearest feature epochs.
3. With half-window `w = 1` by default, form a symmetric transition vector
   `v_i = mean(z[t_i+1 : t_i+w+1]) - mean(z[t_i-w : t_i])`.
4. Normalize valid nonzero transition vectors and use their mean off-diagonal pairwise cosine similarity as the primary score.
5. Build the null by circularly shifting all event centers through the valid interior of the **fixed PCA trajectory**. The EEG trajectory is not shuffled or refit.
6. Aggregate runs by subject and apply the same deterministic development/held-out split as Gates 1A/1B.

The primary numerical rule remains aggregate one-sided permutation `p <= 0.05` plus positive direction in at least `2/3` of held-out subjects. Because the hypothesis was selected after Gate 1B on the same subjects, a PASS would mean only that repeated transition geometry is present in this follow-up analysis.

Synthetic tests freeze two distinctions before the real Gate-1C receipt is inspected: a repeatedly injected event-locked transition direction passes, while a smooth trajectory that is merely periodic at the correct interval does not automatically pass.

### Secondary history diagnostic

Gate 1C also records, without using it for the primary verdict, whether transition vectors are more similar after the same preceding task label (`T1/T1` or `T2/T2`) than after different preceding labels (`T1/T2`). The reported `history_delta` is

```text
mean cosine(same preceding task) - mean cosine(different preceding task)
```

This is exploratory and explicitly marked `history_diagnostic_is_primary = false` in the receipt.

Run the real follow-up with:

```bash
brainloops gate1c \
  --data "E:\\DocsHouse\\575 45 degree angle is real in brain\\physionet.org\\files" \
  --n-null 99 \
  --output results/receipts/gate1c-eegmmidb.json \
  --resume
```

The receipt records `analysis_scope = post_gate1b_followup_same_dataset`. Whatever Gate 1C finds, Gate 1B remains `FAIL` and the original LEMON advancement criterion remains unsatisfied.
