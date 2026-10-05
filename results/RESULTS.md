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

Publication recovery on 5 October 2026 restored the full receipt alongside
`results/receipts/gate1c-eegmmidb-summary.json`. Its 5,245,933 bytes have SHA-256
`b3be8457075207b30978bd7c057a6197df1af2ff935970c7cdb84c87058e508b`, exactly matching
the previously committed summary. All 22 audited hash/count/numerical summary
fields were recomputed without a mismatch. The original EDF analysis was not
rerun during recovery. Receipt checksums are listed in
[`receipts/SHA256SUMS`](receipts/SHA256SUMS).

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

The EEGMMIDB finding is a reproducible event-aligned state-space transformation.
The separately approved R1 result below finds resting temporal structure, with
state return reaching a stronger null tier than transition recurrence. These
results do not identify a literal anatomical cycle or establish transfer of an
event-derived motif into rest.

## R1 — spontaneous/resting transition recurrence

Status: **canonical real LEMON PASS_LINEAR in EC and EO; state recurrence dominates the null tiers**.

Frozen question:

> Can resting EEG repeatedly express the same local state-space transformation even when it does not return to the same state?

R1 is an independent-dataset follow-up motivated by EEGMMIDB Gate 1C. It does not rewrite or retroactively rescue Gate 1B.

The canonical synthetic receipt `results/receipts/r1-synthetic.json` passes at `n_null = 99` and `seed = 1`:

- iid noise: no robust transition recurrence;
- stable linear rotation: linear-lag transition recurrence;
- drifting repeated transform: transition recurrence outranks matched state recurrence, yielding a transformation-only interpretation;
- repeated state return with variable transition direction: state recurrence dominates, preventing a transformation-only label.

The [full real receipt](receipts/r1-lemon-full.json) was uploaded on 5 October
2026 in commit `392f74796354c0ba9a7fb914170c32886c252793`. Its original 839,585
bytes have SHA-256
`5035a94994e15e2c577021f01016af6c3ae00f02da669df2272974dda4c4f632`.
The [analysis](../docs/analysis/2026-10-05-r1-lemon.md) and
[compact summary](receipts/r1-lemon-full-summary.json) record the result and audit.

Observed canonical result:

- 26 discovered subjects: three development, 23 held out.
- 22 usable held-out subjects in EC and the same 22 in EO; 99 null replicates.
- 50 successful subject-condition rows, each with eight usable physical blocks.
- `sub-032309` skipped in both conditions for fewer than four usable blocks.
- Both conditions: transition `LINEAR_LAG_RECURRENCE`, state
  `BEYOND_LINEAR_RECURRENCE`, interpretation `STATE_RECURRENCE_DOMINANT`.

| Condition | Metric / null | Real median | Aggregate null median | p | Positive subjects | Pass |
|---|---|---:|---:|---:|---:|---|
| EC | Transition / order | 0.050347 | 0.036764 | 0.01 | 22/22 | Yes |
| EC | Transition / phase | 0.050347 | 0.048791 | 0.36 | 14/22 | No |
| EC | State / order | −11.920239 | −12.380572 | 0.01 | 18/22 | Yes |
| EC | State / phase | −11.920239 | −12.814981 | 0.01 | 22/22 | Yes |
| EO | Transition / order | 0.049855 | 0.036719 | 0.01 | 19/22 | Yes |
| EO | Transition / phase | 0.049855 | 0.048744 | 0.37 | 9/22 | No |
| EO | State / order | −12.036341 | −12.711920 | 0.01 | 19/22 | Yes |
| EO | State / phase | −12.036341 | −13.154539 | 0.01 | 22/22 | Yes |

Each comparison needs `p <= 0.05` and at least two-thirds positive subjects.
Every real/null subject statistic maximizes over the same frozen lag grid, then
the population takes medians across subjects. `p = 0.01` is the 99-null resolution
floor. Positive direction is not individual significance.

The transition result supports temporal ordering effects compatible with the
phase null's retained linear lag structure. Failing to reject that null does not
prove all neural dynamics linear. State return exceeds both controls, but the
phase tier remains an operational surrogate result: it does not isolate a
nonlinear neural mechanism from distributional, nonstationary, or preprocessing
effects. State-tier dominance does not compare effect sizes in different units.
The transformation-without-matched-state-return dissociation was not the
population result.

EO agreement is within-dataset replication in the same people. LEMON supplies a
separate dataset from EEGMMIDB, without retroactively converting Gate 1C into an
independent confirmatory test.

The public source header/marker and confirmed EEG byte length for `sub-032309`
reproduce the reported 313-annotation warning in a metadata-only check. The
signal length implies approximately 389 seconds, while markers continue to
1,045 seconds, leaving three blocks per condition. This is consistent with the
receipt's exclusion; local Windows file identity was not checked. See the
[source metadata audit](../docs/analysis/r1-lemon-source-metadata-audit.json).

Held-out median clipped feature-value fractions are 4.55% EC and 5.59% EO.
EC clipping burden versus transition/order effect has Pearson `r = −0.121` and
Spearman `r = −0.062`, `n = 22`; these descriptive diagnostics do not establish
artifact-free EEG.

The saved-output audit passes 1,807 checks without a mismatch, including
independent arithmetic and frozen-runner recomputation of all population null
arrays/verdicts. This did not rerun the 26 EEG recordings. Exact installed git
revision, dependencies, raw-file checksums, per-block spectra, and usable-pair
counts are not recorded in the receipt.

The original Gate-1B dataset ladder remains frozen. R1 is a separately approved independent follow-up branch motivated by Gate 1C, not a reinterpretation of the Gate 1B failure.

## Interpretation update — inhibitory feedback and resonance valves

The [5 October interpretation note](../docs/interpretation/2026-10-05-resonance-valves.md)
connects temporal persistence, amplification, and activity-dependent inhibitory
control as a testable hypothesis. The present EEG results do not identify that
controller, demonstrate a reset, or establish an anti-seizure function.

Gate 1C compares normalized transition directions. A monotonic trajectory with
identical increments at event times scores 1.0 without returning to a state or
reducing its magnitude. Its PASS therefore remains a transition-geometry result.
R1 finds resting transition/order recurrence and stronger state-return evidence
under its null tiers. It does not test a frozen task-derived T0 template or a
cell-specific mechanism.

Recovery consolidated the existing R1 source and regenerated its canonical
synthetic receipt at seed 1 and 99 nulls. The four frozen controls pass. The
canonical real LEMON receipt is now present and analyzed above. Neither result
establishes an inhibitory controller, reset, or anti-seizure function.

## Dataset ladder

Phase 1 uses **EEGMMIDB** as a known-clock instrument test, not as the primary intrinsic-loop dataset.

Gate 1B failed its frozen phase-alignment rule, so the planned **LEMON (MPI Leipzig Mind-Brain-Body EEG)** resting-state step remains blocked under the original advancement criterion. Gate 1C is a mechanistic follow-up on EEGMMIDB and does not reopen that ladder by itself.

**CHB-MIT** is reserved for later long-duration/pathology stress testing. It will not be pooled with healthy resting EEG or used to claim normal brain-loop organization.

LEMON/Gates 2–3 and the MultipleTemporalLenses memory bridge/Gate 4 remain deferred under the original ladder.
