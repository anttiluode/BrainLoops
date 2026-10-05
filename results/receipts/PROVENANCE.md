# Receipt provenance

[`SHA256SUMS`](SHA256SUMS) records the exact bytes of the six JSON receipts in this
directory. The receipt filenames in that manifest are relative to this directory.
Git attributes preserve these files' original line endings across platforms,
including the restored Gate 1C receipt's Windows CRLF bytes.

| Receipt | Origin |
|---|---|
| `gate0-synthetic.json` | Existing Phase 1 calibration, preserved during recovery |
| `gate1-eegmmidb.json` | Existing full Gate 1A result, preserved during recovery |
| `gate1b-eegmmidb.json` | Existing full Gate 1B result, preserved during recovery |
| `gate1c-eegmmidb-summary.json` | Previously published compact Gate 1C summary, preserved during recovery |
| `gate1c-eegmmidb.json` | Restored original full result; bytes and SHA-256 match the compact summary |
| `r1-synthetic.json` | Regenerated on 5 October 2026 from the complete R1 source at `eed199898e12d7d4f4c0c976be443ab90f5a5151`, seed 1 and 99 nulls |

The regenerated R1 command was:

```bash
python -m experiments.r1_synthetic --n-null 99 --seed 1 --output results/receipts/r1-synthetic.json
```

The run used Python 3.12, NumPy 2.3.5, SciPy 1.17.0, and scikit-learn 1.8.0.
All four frozen semantic controls passed. Subsequent recovery fixes change
condition-level integrity handling and receipt publication, not R1 metrics,
null generation, or frozen decision rules.

Gate 1C's restored full receipt is 5,245,933 bytes with SHA-256
`b3be8457075207b30978bd7c057a6197df1af2ff935970c7cdb84c87058e508b`. All 22 audited
hash/count/numerical summary fields match recomputation. This verifies the saved
output; the original EDF processing was not repeated during recovery.

There is no real R1 LEMON receipt yet. The scientific verdicts and limits are in
[`RESULTS.md`](../RESULTS.md).
