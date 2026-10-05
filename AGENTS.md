# Working on BrainLoops

Read `docs/PROJECT_STATE.md`, `results/RESULTS.md`, and current remote `main`
before resuming interrupted work. Historical branches and frozen plans are
evidence of earlier stages, not the current completion checklist.

- Preserve Gate 1B as FAIL and Gate 1C as a post-Gate-1B same-dataset follow-up.
- Keep measured transition geometry separate from hypotheses about anatomical
  loops, inhibitory cells, neural resets, epilepsy, or consciousness.
- Real LEMON results remain pending until a real receipt is produced. Synthetic
  calibration does not establish a resting EEG result.
- Publish ordinary source, docs, tests, and receipts in coherent commits. Do not
  use temporary payload bundles, generated wheels, or partial staging files as
  the repository's implementation.
- A claim that a receipt is committed must point to an existing file. Preserve
  receipt bytes and record checksums when recovering results.
- Before integrating code, run `python -m pytest -q` and the affected synthetic
  gate. For documentation or receipt-only changes, check local links, JSON,
  checksums, and consistency with the results ledger.
- Keep raw EEG, caches, virtual environments, and build output out of git.
- Update the project checkpoint after a completed milestone or interruption.
  Record what actually finished, the source revision, verification, and the next
  unfinished step so a later session can continue without replaying the work.
