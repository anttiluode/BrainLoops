## R1 — resting transition recurrence

R1 is a new independent-dataset branch motivated by EEGMMIDB Gate 1C. Gate 1C suggested that an experimentally defined boundary can repeat a local **direction of state change** even when Gate 1B did not return to the same coarse state. R1 asks whether analogous transition geometry recurs spontaneously within resting EEG blocks, without an external task clock selecting candidate times.

Canonical R1 v1 uses raw **LEMON / Leipzig Mind-Brain-Body BrainVision** recordings so the physical alternating eyes-open (EO) and eyes-closed (EC) block markers are preserved. Condition-split files that may have concatenated block boundaries are intentionally not accepted as the canonical path.

The frozen primary condition is **EC**; EO is a preregistered within-dataset replication and cannot rescue an EC failure. EEG features use 0.5 s epochs, one PCA basis per subject/condition, physical blocks remain separate for recurrence calculations, and the fixed lag grid is 2.0–20.0 s in 0.5 s steps. Every real and null replicate takes its own maximum over that complete lag grid.

Transition recurrence compares local displacement-vector directions. Matched state recurrence uses continuous PCA-state return distance. Both are tested against an order-destroying null and a multivariate phase-preserving linear-lag null. Outcomes are:

- `NO_ROBUST_RECURRENCE`
- `LINEAR_LAG_RECURRENCE`
- `BEYOND_LINEAR_RECURRENCE`

The strongest dissociation is transition recurrence without matched state recurrence at the same null tier. Joint transition+state recurrence is retained as a narrower positive result rather than relabeled as failure.

### Calibration

The committed synthetic R1 gate passes all frozen semantic controls at 99 nulls:

```bash
brainloops r1-synthetic --n-null 99 --seed 1 --output results/receipts/r1-synthetic.json
```

### Real LEMON run

A real LEMON receipt is **pending**. No real-data verdict is inferred from the synthetic calibration.

```bash
brainloops r1-lemon \
  --data /path/to/lemon-raw \
  --n-null 99 \
  --output results/receipts/r1-lemon.json \
  --resume
```

Windows:

```bat
brainloops r1-lemon --data "E:\path\to\lemon-raw" --n-null 99 --output results\receipts\r1-lemon.json --resume
```

The canonical R1 receipt requires at least 20 usable held-out EC subjects and at least 19 null replicates; otherwise it reports `INSUFFICIENT_DATA`.

R1 is an explicitly approved independent follow-up branch motivated by Gate 1C. It does **not** rewrite the frozen Gate 1B result or retroactively satisfy the original Gate-1B-to-LEMON advancement rule.
