# BrainLoops project checkpoint

Updated: 5 October 2026.

## Current state

The repository contains Phase 1, Gate 1B, Gate 1C, and the R1 resting-transition
implementation. The scientific ledger is [`results/RESULTS.md`](../results/RESULTS.md).

| Experiment | Implementation and evidence | Next unfinished step |
|---|---|---|
| Gate 0 | Synthetic PASS; canonical receipt present | No unfinished Phase 1 calibration task |
| Gate 1A | 109-subject PASS with occupancy-shuffle limitation | Preserve as timescale positive control |
| Gate 1B | 109-subject FAIL; full receipt present | Preserve the failure and original ladder |
| Gate 1C | 109-subject PASS; original full receipt and compact summary present | Independent confirmation, not reinterpretation as a reset |
| Gate 1C history diagnostic | Negative median; not supported | Exploratory only |
| R1 synthetic | Four frozen controls PASS at seed 1, 99 nulls; receipt present | Calibration complete |
| R1 real | Canonical EC and EO PASS_LINEAR; 22 usable held-out subjects; full receipt and audited summary present | Independent cohort with predeclared distribution/nonstationarity controls |
| Resonance-valve hypothesis | Interpretation and proposed experiment documented | No inhibitory-controller or seizure experiment implemented |

The original Gate-1B-to-LEMON advancement condition remains unsatisfied. R1 is a
separately approved follow-up; the repository contains its implementation without
claiming that the original ladder advanced.

The latest real result is in the
[R1 LEMON analysis](analysis/2026-10-05-r1-lemon.md). Historical recovery and
adapter checkpoints below describe earlier stages; their then-pending runs have
now been completed. The canonical publication checkpoint near the end records
the current evidence and remaining limits.

## Audited source revisions

- Phase 1 / Gate 1C main before recovery: `a1a5026baa17dd15e6b38fa80a3b8a3ba3e136cc`.
- Complete R1 source before consolidation: `eed199898e12d7d4f4c0c976be443ab90f5a5151`.
- Older Gate 1B publication summary: `e5ca9eff0e3cc058fd65aa56abffbac3d8737034`;
  preserved under [`archive/`](archive/README.md).

## Recovery verification

- Repaired full suite: 99 passed, 1 skipped. The skip requires an external real
  EEGMMIDB dataset; it is not a skipped synthetic gate.
- Canonical R1 synthetic run: seed 1, 99 nulls, all four controls PASS.
- Restored Gate 1C receipt: original SHA-256 matches; all 22 audited summary
  fields match the recomputed values.
- The actual Gate 1C scoring function gives 1.0 on a steadily increasing
  trajectory, confirming that direction consistency alone is not a reset test.
- Packaging is covered by the full suite's wheel-build test.
- Four added regressions failed on the original code and pass after the repairs:
  condition-scoped PCA failures, valid EC preservation when EO is constant,
  persistence of the initial split, and preservation of the previous receipt
  during an interrupted write.

No original EEGMMIDB EDF reprocessing or real LEMON run is claimed by these checks.

R1 adapter tests use controlled Raw fixtures; there is no real LEMON smoke test
in the current suite. The first representative raw-data run must therefore check
actual file/marker compatibility. R1 receipts retain subject spectra and usable
block counts, but do not yet retain per-block spectra and usable-pair counts from
the original spec. That is an auditability limitation of the current output.

## R1 input-diagnostics follow-up

The follow-up starts from consolidated main
`e410d8dd462885fff7590665b2ac524d787d8090`. An EEGMMIDB-only directory previously
discovered zero LEMON subjects, wrote an empty receipt, and printed only
`INSUFFICIENT_DATA`. The runner now rejects that input before touching the output.
Valid but insufficient LEMON runs print the discovered, usable held-out EC,
null, and skipped subject-condition counts. The README includes the separate raw
LEMON download, extracted layout, and fresh-receipt requirement when switching
datasets. Scientific criteria and existing receipt contents are unchanged.

- Full suite: 101 passed, 1 skipped (external EEGMMIDB dataset unavailable).
- Both new diagnostic regressions failed on the previous main and now pass.
- R1 synthetic: seed 1, 99 nulls, PASS; output matches the canonical JSON exactly.
- Both CLI entry points reject EDF-only input with exit code 2 and preserve an
  existing receipt, including with `--resume`.
- Independent code review approved the focused change; `git diff --check` passed.

The next unfinished step remains a real raw LEMON run, not another EEGMMIDB run.

## Eight-subject exploratory path and loader compatibility

Base revision: `7cc02d40d871c9c31b1bb2607b1a4462eda72734`. The user reported
eight discovered raw LEMON subjects, zero usable held-out EC subjects, and 16
skipped conditions. Their receipt and exact skip reasons were not provided.

The raw-file adapter now handles a documented LEMON renaming issue: missing
older-ID references can resolve to the header's existing same-stem companions.
A real MNE reader fixture reproduced the failure before the fix. Temporary
corrected headers and markers respect source codepages and use UTF-8 consistently,
including non-ASCII filesystem paths; downloaded source bytes remain untouched.
This repairs a reproduced likely cause, not a confirmed diagnosis of the user's
particular skipped rows.

`--exploratory` reports the same recurrence/null statistics with one or more
usable held-out EC subjects while retaining the canonical 20-subject verdict
separately. Results are prefixed `EXPLORATORY_`; splits, physical blocks, lag/null
definitions, EC/EO roles, and significance/direction rules are unchanged.
`--resume --retry-skipped` preserves completed rows and retries failed conditions.
The CLI now prints up to five distinct skip reasons.

- Full suite: 108 passed, 1 skipped (external EEGMMIDB data unavailable).
- New feature/loader regressions failed before implementation; ANSI/non-ASCII
  path regressions exposed and verified the repair of a code-review finding.
- Synthetic R1: seed 1, 99 nulls, PASS; JSON matches the canonical receipt exactly.
- End-to-end generated BrainVision check: eight subjects, 99 nulls, all 16
  conditions processed, seven usable held-out EC subjects, zero skips. This
  generated-data check is not a real LEMON result.
- Independent code review approved after the encoding repair; `git diff --check`
  passed.

Next: install current main and run the user's eight actual raw subjects with
`--exploratory` and a fresh output filename. Retain that actual receipt, including
any remaining skip reasons. The canonical 20-subject real-data result is pending.

## Raw LEMON refresh-marker repair

Base revision: `183a11bd954cf44252d6647700760f55a81ff6d3`. The user subsequently
reported 26 discovered subjects, zero usable held-out EC subjects, and 52 skipped
conditions with the reason `EO/EC rest markers must alternate`. One MNE warning
reported 313 annotations outside the data range.

The alternation failure was reproduced on a complete official raw recording.
The GWDG `sub-010002`, `sub-010003`, and `sub-010004` marker files each contain
480 EO/EC pulses: 30 two-second condition refreshes per physical block, across
16 alternating blocks. Observed adjacent same-condition gaps were
1.9996–2.0004 seconds. The former parser incorrectly required every pulse to
alternate. The adapter now coalesces the known two-second refresh cadence,
allowing 20 ms for clock/resampling rounding, while retaining every condition
change as a physical boundary. Other duplicate gaps and non-increasing or
out-of-range onsets still fail explicitly. The last-block-to-recording-end
convention, recurrence/null calculations, splits, and numerical criteria remain
unchanged. This corrects a dataset-format assumption, not a result-selection rule.

- Four new refresh-pattern regression cases failed before the fix and now pass.
- Focused adapter/runner tests: 39 passed. Full suite: 113 passed, 1 skipped
  (external EEGMMIDB data unavailable).
- Synthetic R1: seed 1, 99 nulls, PASS; JSON matches the canonical receipt exactly.
- Actual raw smoke checks: the public S3 archives for `sub-032301` and
  `sub-032344` each yield eight usable EC and eight usable EO feature blocks.
  The `sub-032301` CLI run processed both conditions with 99 nulls and zero skips.
  Its one-subject exploratory status was `EXPLORATORY_FAIL`; the canonical
  status was `INSUFFICIENT_DATA`. This compatibility check is not a canonical
  population result, and its diagnostic receipt is not committed as one.
- The first S3 archive's header/marker bytes match the older-ID GWDG metadata;
  real MNE loading also exercises the renamed-companion repair.
- Independent review approved the parser; `git diff --check` passed.

Neither downloaded smoke-check recording emitted the user's clipped-annotation
warning. Its cause in the user's local set remains unconfirmed and is separate
from refresh-marker parsing; the repair does not restore absent data or assert
that all 26 recordings are usable. Raw downloads remain outside git.

Next: update the installed command and run the user's larger actual set without
`--exploratory`, using a fresh `r1-lemon-full.json` receipt. At least 20 usable
held-out EC subjects are required; 26 downloads do not guarantee that count.
Retain the actual receipt and investigate any remaining condition skip reasons.

## Resume here

1. Fetch current remote main and read this checkpoint. Inspect any open PR's
   current head before working; do not restart from an older staging branch.
2. The canonical R1 run is complete and retained. Read its
   [analysis](analysis/2026-10-05-r1-lemon.md) and
   [provenance](../results/receipts/PROVENANCE.md) before proposing another study.
   Preserve EC/EO roles, physical block boundaries, the frozen verdict, and the
   original receipt bytes.
3. A new EEG study should predeclare broader multivariate distribution and
   nonstationarity controls, verify their preserved constraints, and use an
   independent cohort. It is a follow-up, not a repair of this saved result.

The resonance-valve experiment is a later proposed test, not an unfinished task
hidden inside R1. Its requirements are in the
[interpretation note](interpretation/2026-10-05-resonance-valves.md#next-informative-tests).

## Canonical R1 result publication

Source base: `392f74796354c0ba9a7fb914170c32886c252793`, which adds the user's
full real LEMON receipt on top of the refresh-marker repair. The attachment and
committed receipt match byte for byte: 839,585 bytes, SHA-256
`5035a94994e15e2c577021f01016af6c3ae00f02da669df2272974dda4c4f632`.

- 26 subjects: three development and 23 held out. Excluding `sub-032309` in both
  conditions leaves the same 22 usable people in EC and EO. Each successful
  condition has eight physical blocks; 50/52 rows succeed; 99 nulls are recorded.
- Both conditions have transition `LINEAR_LAG_RECURRENCE`, state
  `BEYOND_LINEAR_RECURRENCE`, and `STATE_RECURRENCE_DOMINANT`. Canonical EC and
  replication EO both report `PASS_LINEAR`. The phase-null label remains an
  operational result with distributional/nonstationarity limits.
- A fresh saved-output audit passes 1,807 checks with zero mismatches, including
  independent arithmetic and frozen-runner recomputation of the full population
  dictionaries. The 26 EEG recordings were not reprocessed.
- The public S3 metadata for `sub-032309` match official older-ID `sub-010015`
  metadata. The source EEG byte length implies 388.9876 seconds; markers extend
  to 1,045.2412 seconds. A metadata-only MNE read reproduces the 313-annotation
  warning and leaves three blocks per condition. This is consistent with the
  receipt exclusion; local-file identity remains unchecked.
- The main README, results ledger, analysis, figure, compact summary, provenance,
  and checksum manifest now agree. Documentation/receipt verification checks
  local links, JSON, exact checksums, table values, and unchanged earlier receipts.
  No scientific metric, threshold, split, or loader behavior is changed.

Next: an independently designed EEG follow-up or the separately proposed
feedback/gain experiment. No unfinished canonical R1 run remains.
