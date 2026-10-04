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

## Gate 1B — fixed-timeline phase alignment

Status: implementation complete; real EEGMMIDB receipt pending.

Gate 1B asks a stricter question while leaving the EEG-derived state timeline untouched:

1. Fit PCA/K-means state trajectories without annotations at `k = 6, 10, 20`.
2. Convert successive `T0` onsets to feature-epoch indices.
3. Measure the fraction of consecutive `T0` pairs that return to the same unsupervised state, averaged equally across the three coarse-grainings.
4. Generate the null by circularly shifting the `T0` indices across the **fixed** state timeline. The EEG state sequence itself is never shuffled.
5. Aggregate runs by subject and use only held-out subjects for the confirmatory verdict.

The null preserves the complete state trajectory, including occupancy, dwell, autocorrelation, and recurrence. It changes only the external phase assignment.

Two synthetic controls freeze the intended distinction: an event-locked state anchor passes, while a trajectory that is merely periodic at the correct period but has no privileged `T0` phase does not automatically pass.

Run the real gate with:

```bash
brainloops gate1b \
  --data "E:\\DocsHouse\\575 45 degree angle is real in brain\\physionet.org\\files" \
  --n-null 99 \
  --output results/receipts/gate1b-eegmmidb.json \
  --resume
```

The confirmatory rule remains aggregate `p <= 0.05` plus positive direction in at least `2/3` of held-out subjects. LEMON remains blocked until this receipt exists and survives that rule.
