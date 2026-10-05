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
| R1 real | Adapter, runner, nulls, CLI, and tests implemented | Run raw LEMON and retain its real receipt |
| Resonance-valve hypothesis | Interpretation and proposed experiment documented | No inhibitory-controller or seizure experiment implemented |

The original Gate-1B-to-LEMON advancement condition remains unsatisfied. R1 is a
separately approved follow-up; the repository contains its implementation without
claiming that the original ladder advanced.

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

## Resume here

1. Fetch current remote main and read this checkpoint. Inspect any open PR's
   current head before working; do not restart from an older staging branch.
2. For the existing R1 experiment, obtain raw LEMON BrainVision data and run the
   documented `brainloops r1-lemon ... --resume` command. EC is primary and EO
   is replication; retain physical block boundaries and frozen criteria.
3. Review the real receipt and update the results ledger with its actual verdict,
   skipped/malformed recordings, and artifact diagnostics.

The resonance-valve experiment is a later proposed test, not an unfinished task
hidden inside R1. Its requirements are in the
[interpretation note](interpretation/2026-10-05-resonance-valves.md#next-informative-tests).
