# Recovery after interrupted sessions

Date: 5 October 2026.

Antti reports that repeated starts and forced session endings at timeouts caused
the repository disorder. The history contains multiple staging/publication
attempts and branches from those attempts. This record makes current main the
starting point for further work while preserving the earlier evidence.

## What was reconciled

- Phase 1, packaging, Gate 1B, and Gate 1C source were already present on main.
- PR #4 held the complete R1 source. It was verified, repaired for condition-level
  failures, and consolidated with the interpretation and recovery work.
- The full Gate 1C result receipt was absent from main. Its original bytes were
  recovered and matched the SHA-256 in the existing compact summary. All 22
  audited summary fields match their recomputation.
- The R1 README and results ledger referred to a synthetic receipt removed during
  publication cleanup. It was regenerated from the R1 source at seed 1 and 99
  nulls, and all four frozen controls pass.
- The older Gate 1B summary branch held two unique files. Their original bytes
  are preserved in [`archive/`](archive/README.md), with the workflow retained as
  text rather than installed as another active publication job.
- The placeholder `.gitkeep` was removed from the populated receipts directory.
  Ignore rules now cover build output, environments, caches, raw EEG, and receipt
  staging files.

## Historical branch map

The SHAs below are the heads observed before this recovery. Older branch refs are
retained as recovery pointers; current implementation and results are on main.

| Branch | Observed head | Reconciliation |
|---|---|---|
| `main` | `a1a5026baa17dd15e6b38fa80a3b8a3ba3e136cc` | Phase 1 and Gate 1C baseline |
| `feature/brainloops-phase1` | `5572a3c83e0e9171957bf1571cf684c2efd7d03e` | Already contained in main |
| `fix/package-discovery` | `c1ef4179b6ace67bb33084f9dd73344ac404d8d5` | Already contained in main |
| `feature/gate1b-phase-alignment` | `2f88f9856a5c8a441bfd492d5816680ba1417daf` | Already contained in main |
| `feature/gate1c-transition-geometry` | `e0fc7e62d3af886cc2a4fd54bb976719fa0a071a` | Already contained in main |
| `results/gate1c-pass` | `97feb9a4c17db96cf1bc19a1273d8e8ae5333eab` | Already contained in main |
| `spec/r1-spontaneous-transition-recurrence` | `8f320391f61c631356469113532c468448c8ea82` | Spec/plan contained in the complete R1 branch |
| `feature/r1-resting-transition-recurrence` | `eed199898e12d7d4f4c0c976be443ab90f5a5151` | Complete R1 source; reviewed and consolidated |
| `analysis/gate1b-receipt-summary` | `e5ca9eff0e3cc058fd65aa56abffbac3d8737034` | Unique summary/helper preserved under archive |

## Interruption handling repaired

R1 now records expected validation failures as condition-specific SKIP rows and
continues with other conditions and subjects. Degenerate PCA no longer aborts the
entire population run. A constant or otherwise invalid EO condition no longer
discards valid primary EC data; the receipt retains the condition's failure
reason.

The deterministic subject split and configuration are saved before the first
recording is processed. Receipt writes stage a complete JSON file in the same
directory and atomically replace the destination. An interrupted staging write
therefore leaves the previous complete checkpoint available for `--resume`.
This addresses process interruptions, rather than claiming protection against
every filesystem or hardware failure.

Four regression tests reproduced these failures before the changes and pass
afterward. The repaired full suite reports 99 passed and one external EEGMMIDB
data test skipped. R1's real LEMON adapter remains unverified on a representative
raw recording; its current receipt also lacks the spec's per-block spectra and
usable-pair counts. These limits are retained in the project checkpoint.

## Scientific conclusions preserved

Gate 1B remains FAIL. Gate 1C remains a post-Gate-1B same-dataset transition
result, and its preceding-task history diagnostic remains unsupported. Real
LEMON data and an R1 real-data receipt are still pending.

The [resonance-valve note](interpretation/2026-10-05-resonance-valves.md) records a
plausible inhibitory-feedback hypothesis and a proposed joint memory/stability
test. It does not relabel existing EEG scores as resets or seizure protection.

## Resume without replaying the work

Use [`PROJECT_STATE.md`](PROJECT_STATE.md) and current main. Publish normal source
and receipts in coherent commits, update the checkpoint with actual verification,
and record the next unfinished task. A frozen design's earlier "not started"
status is historical evidence, not a reason to restart implemented work.
