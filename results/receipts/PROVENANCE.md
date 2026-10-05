# Receipt provenance

[`SHA256SUMS`](SHA256SUMS) records the exact bytes of the eight JSON receipts in this
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
| `r1-lemon-full.json` | User's canonical Windows LEMON run; uploaded to main in `392f74796354c0ba9a7fb914170c32886c252793`, exact bytes match the attachment |
| `r1-lemon-full-summary.json` | Derived saved-output audit and compact summary on 5 October 2026; no original EEG reprocessing |

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

The real R1 LEMON receipt is 839,585 bytes, SHA-256
`5035a94994e15e2c577021f01016af6c3ae00f02da669df2272974dda4c4f632`.
It records seed 0, 99 nulls, package version `0.1.0`, 26 discovered subjects,
and the canonical EC-primary / EO-replication configuration. Its configuration
fingerprint is
`a2d2da3d93b76cc8e87074abdb986fbe8bfe4e501f3597e4d0c4e039f349d4e6`.
The exact installed git revision, dependency versions, and raw-file checksums
were not recorded. The summary's audited source revision identifies the code
used for saved-output recomputation, not a recovered execution environment.

The fresh audit against source `392f74796354c0ba9a7fb914170c32886c252793` passes
1,807 checks with zero mismatches. It verifies source bytes, configuration/splits,
complete subject-condition rows, subject spectra/statistics/nulls, population
null arrays and classifications, and artifact diagnostics. Independent arithmetic
and the frozen runner reproduce both population result dictionaries. It does
not rerun the 26 EEG recordings. Earlier receipts are unchanged.

A separate public-source metadata/file-length check reproduces the reported
313-annotation warning for excluded `sub-032309`. Its
[audit record](../../docs/analysis/r1-lemon-source-metadata-audit.json) explicitly
uses a sparse placeholder for metadata loading only; it contains no EEG analysis
or raw EEG. The local Windows files were not inspected.

The [full LEMON interpretation](../../docs/analysis/2026-10-05-r1-lemon.md) and
[`RESULTS.md`](../RESULTS.md) distinguish the measured verdicts from hypotheses.
