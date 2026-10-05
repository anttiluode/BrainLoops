## R1 — spontaneous/resting transition recurrence

Status: **implementation and synthetic calibration complete; real LEMON receipt pending**.

Frozen question:

> Can resting EEG repeatedly express the same local state-space transformation even when it does not return to the same state?

R1 is an independent-dataset follow-up motivated by EEGMMIDB Gate 1C. It does not rewrite or retroactively rescue Gate 1B.

The canonical synthetic receipt `results/receipts/r1-synthetic.json` passes at `n_null = 99` and `seed = 1`:

- iid noise: no robust transition recurrence;
- stable linear rotation: linear-lag transition recurrence;
- drifting repeated transform: transition recurrence outranks matched state recurrence, yielding a transformation-only interpretation;
- repeated state return with variable transition direction: state recurrence dominates, preventing a transformation-only label.

The real R1 analysis is not complete until raw LEMON BrainVision data are run under the frozen EC-primary / EO-replication configuration. No real LEMON result is claimed here.

The original Gate-1B dataset ladder remains frozen. R1 is a separately approved independent follow-up branch motivated by Gate 1C, not a reinterpretation of the Gate 1B failure.
