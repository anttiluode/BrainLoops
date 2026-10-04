# BrainLoops R1 — Spontaneous Transition Recurrence

Date: 2026-10-04
Status: design approved in chat; implementation not started
Scope: independent-dataset follow-up motivated by EEGMMIDB Gate 1C

## Question

> **Can spontaneous resting EEG repeatedly express the same local state-space transformation even when it does not return to the same state?**

This question is motivated by the conjunction of the frozen EEGMMIDB results:

- Gate 1B: the true `T0` phase did **not** preferentially return to the identical coarse state.
- Gate 1C: the true `T0` phase **did** repeatedly express a similar local direction of change in continuous PCA state space.

R1 asks whether an analogous phenomenon exists without an external task clock.

R1 is a new branch of evidence. It does not reopen or rewrite the original Gate-1B-to-LEMON advancement rule, and it does not retroactively change any Gate 1 result. The hypothesis was generated on EEGMMIDB and is tested on a different dataset.

## Dataset and independence

Primary dataset: **LEMON / Leipzig Mind-Brain-Body EEG resting-state data**.

The implementation will consume the public resting-state EEG and its eyes-open / eyes-closed block annotations or equivalent BIDS metadata. Raw EEG is never committed to the repository.

The two conditions are analyzed separately:

- **Eyes closed (EC)** is the preregistered primary condition.
- **Eyes open (EO)** is a preregistered within-dataset replication / robustness condition.

No condition may be selected after seeing the results.

Subjects are split deterministically before the primary receipt is inspected:

- development: 20% of usable subject IDs selected by a stable hash rule fixed in code;
- held out: remaining 80%.

All threshold tuning, parser fixes, and synthetic calibration must be completed using synthetic data and/or the development split. The held-out split is evaluated once under the frozen configuration.

## Representation

R1 reuses the existing BrainLoops EEG feature pipeline where possible:

- 0.5 s feature epochs;
- robust median/MAD scaling and clipping with artifact statistics reported;
- all available EEG channels after the same normalization rules used elsewhere in BrainLoops;
- no task/event labels are used to construct the latent trajectory.

For each subject and condition, all usable blocks of that condition are pooled only for fitting an up-to-8-dimensional PCA basis. Each physical block is then transformed separately and all recurrence calculations remain strictly within block boundaries. No transition or lag pair may cross a block boundary.

This gives a common subject-condition coordinate system without introducing artificial transitions between noncontiguous blocks.

## Local transition vectors

For each interior epoch `t` in a block, with the Gate-1C-compatible default half-window `w = 1` epoch:

```text
v_t = mean(z[t+1 : t+w+1]) - mean(z[t-w : t])
```

With `w = 1`, this is a symmetric 0.5 s-before / 0.5 s-after local displacement around `t`.

Only finite, nonzero vectors are retained for cosine calculations. Vector magnitude is not part of the primary transition-recurrence statistic; the primary question is recurrence of **direction**.

## Transition recurrence spectrum

The preregistered lag grid is:

```text
2.0 s, 2.5 s, ..., 20.0 s
```

At each lag `tau`, using only within-block pairs:

```text
R_v(tau) = median cosine(v_t, v_{t+tau})
```

The minimum lag avoids trivial overlap/local smoothness around adjacent transition vectors. The maximum lag stays well inside the approximately minute-scale resting blocks while spanning the multi-second scales that motivated BrainLoops.

The real per-subject-condition transition statistic is the **maximum over the entire preregistered lag grid**:

```text
M_v = max_tau R_v(tau)
```

The same maximization is performed independently inside every null replicate. This max-statistic is the multiple-lag correction; no lag may be selected after results are seen.

The lag achieving the real maximum is reported descriptively but is not treated as an anatomical or intrinsic circuit period.

## Matched state recurrence

R1 measures state recurrence in parallel so that transition recurrence is not automatically interpreted as a return to the same state.

Within each subject-condition PCA representation, component scores are standardized using the real-data component scale. For each lag:

```text
R_z(tau) = - median ||z_t - z_{t+tau}||^2
```

Higher `R_z` therefore means closer return in continuous state space.

The corresponding max statistic is:

```text
M_z = max_tau R_z(tau)
```

The exact same lag grid, within-block restrictions, and max-over-lags procedure are used for real and null data.

This is deliberately continuous. R1 does not introduce a new K-means state count.

## Nulls

R1 uses two null layers because BrainLoops treats linear-lag recurrence as a legitimate positive class rather than as a failed nonlinear class.

### Null A — order-destroying marginal null

Within each physical block, independently permute the order of the derived transition vectors for the transition statistic and the order of standardized PCA state vectors for the state statistic.

This preserves the corresponding marginal vector/state distributions and sample counts but destroys temporal ordering.

The same preregistered lag scan and max statistic are applied to every replicate.

Purpose: ask whether there is temporal recurrence at all beyond the marginal geometry of the representation.

### Null B — multivariate phase-preserving linear-lag null

Within each block, apply a multivariate phase-randomized surrogate to the continuous PCA trajectory using a shared random phase per frequency across PCA dimensions, preserving the block's linear auto/cross-spectral structure and relative linear phase relationships while removing higher-order temporal organization.

Recompute transition and state recurrence spectra from each surrogate trajectory, including the full lag scan and max statistic.

Purpose: separate recurrence explainable by linear spectral/phase structure from recurrence beyond that null.

No anatomical meaning is assigned to either class.

## Per-subject quantities

For each condition and each subject, report:

- `M_v_real`: maximum transition recurrence;
- `tau_v_peak`: lag of that maximum;
- order-null and phase-null distributions for `M_v`;
- one-sided permutation p-values against each null;
- positive-direction flags relative to each null median;
- `M_z_real`: maximum continuous-state recurrence;
- `tau_z_peak`;
- matched state null distributions, p-values, and positive-direction flags;
- artifact statistics and number of usable blocks/pairs.

Per-block spectra are retained in receipts or resumable intermediate files so aggregation can be audited.

## Population aggregation

The held-out EC split is the primary population test.

For a given statistic/null pair:

1. aggregate physical blocks within subject without crossing block boundaries;
2. use the subject-level real statistic as one observation;
3. aggregate each null replicate across held-out subjects with the median;
4. compare the held-out median real statistic against the distribution of held-out median null statistics;
5. compute the one-sided permutation p-value with the same `(+1)/(n_null+1)` convention used by existing BrainLoops gates;
6. report the fraction of held-out subjects whose real statistic exceeds their own null median.

Primary population success requires:

```text
aggregate p <= 0.05
AND
positive direction in >= 2/3 of held-out subjects
```

The number of null replicates for the canonical receipt is 99, giving a minimum p-value of 0.01.

## Outcome classes

R1 does not collapse all outcomes into one vague `PASS`.

For transition recurrence, classify the primary EC held-out result as:

- **NO ROBUST TRANSITION RECURRENCE**: transition recurrence fails the order-destroying null;
- **LINEAR-LAG TRANSITION RECURRENCE**: transition recurrence beats the order-destroying null but not the phase-preserving null;
- **BEYOND-LINEAR TRANSITION RECURRENCE**: transition recurrence beats both nulls.

Matched state recurrence receives the same three-level classification.

The scientifically strongest dissociation is:

```text
transition class > state class
```

and especially:

```text
transition recurrence present
AND
matched state recurrence absent at the same null tier
```

The receipt therefore reports one of these interpretation labels in addition to the raw transition/state classes:

- `TRANSFORMATION_ONLY_AT_ORDER_TIER`
- `TRANSFORMATION_ONLY_AT_PHASE_TIER`
- `JOINT_TRANSITION_AND_STATE_RECURRENCE`
- `STATE_RECURRENCE_DOMINANT`
- `NO_ROBUST_RECURRENCE`

A transition recurrence result remains scientifically useful even if state recurrence is also present, but only a transformation-only label supports the narrow "same transformation without same state" dissociation.

## Primary success rule

The primary R1 gate asks first whether spontaneous transition recurrence exists in independent resting EEG.

R1 primary EC status is:

- `PASS_LINEAR` if transition recurrence beats the order null under the population rule but not the phase null;
- `PASS_BEYOND_LINEAR` if transition recurrence beats both nulls under the population rule;
- `FAIL` otherwise.

The state-recurrence result is then used to determine whether the pass is transformation-only or joint recurrence. R1 does **not** silently fail a genuine transition-recurrence discovery merely because state recurrence is also present; instead it narrows the claim.

This preserves the BrainLoops convention that linear recurrent structure is a positive computational result.

## Eyes-open replication

EO is analyzed with the exact same frozen configuration after the EC primary verdict is computed.

EO cannot rescue an EC failure. It is reported as:

- same transition class;
- weaker/different transition class;
- no robust recurrence;
- or opposite/ambiguous direction.

Agreement between EC and EO strengthens generality; disagreement narrows the claim to condition-specific resting dynamics.

## Synthetic and negative controls

Before real held-out LEMON evaluation, synthetic tests must demonstrate at least:

1. **iid / temporally permuted vectors** do not pass;
2. **stable linear rotating dynamics** produce linear-lag transition recurrence and are absorbed by the phase-preserving null;
3. **repeated local transform with drifting state** can produce transition recurrence without matched state recurrence;
4. **repeated state return without repeated transition direction** does not automatically produce a transformation-only classification;
5. lag scanning plus max-statistic does not inflate the nominal null pass rate in repeated synthetic null trials beyond the expected permutation behavior.

These controls freeze the meaning of the outcome labels before the held-out LEMON receipt is inspected.

## Artifact and robustness diagnostics

Artifact burden is reported, not silently optimized away.

The primary analysis does not discard subjects merely because a clipping statistic is high unless a predeclared data-integrity threshold is violated (e.g. unreadable/missing data, insufficient usable epochs, nonfinite features).

Secondary diagnostics report correlations between artifact burden and subject-level transition recurrence/effect size. These diagnostics cannot rescue or invalidate the primary gate post hoc; they inform interpretation and possible future replication design.

No alternative PCA dimension, lag range, window width, channel subset, or condition may replace the frozen primary analysis after held-out results are seen. Such variants may be reported only as clearly labeled exploratory sensitivity analyses.

## Claim boundary

A positive R1 result supports only a computational statement about spontaneous scalp-EEG state-space dynamics.

It does **not** identify:

- a hippocampal loop;
- a corticothalamic loop;
- a basal-ganglia loop;
- an apical-dendritic mechanism;
- a consciousness mechanism;
- a literal anatomical cycle;
- a unique biological source for any recurrence lag.

Scalp EEG source mixing and volume conduction make those anatomical assignments unjustified here.

Even `BEYOND-LINEAR TRANSITION RECURRENCE` means only "not explained by this phase-preserving linear surrogate." It is not equivalent to "nonlinear brain circuit proven."

## Relationship to Gate 1C

Gate 1C established, on task-structured EEGMMIDB, that an externally defined `T0` boundary repeatedly carried a similar local PCA transition direction despite Gate 1B's failure of same-state recurrence.

R1 removes the external clock entirely. It asks whether recurrence of transition geometry can be detected from resting dynamics alone.

Therefore:

- EEGMMIDB Gate 1C is hypothesis generation / instrument precedent;
- LEMON R1 is the independent-dataset test;
- success on R1 would justify a later R2 asking whether a richer fitted local operator (for example a local linear map/Jacobian surrogate) recurs;
- failure on R1 stops that operator-expansion path.

## Advancement rule

Only a held-out EC `PASS_LINEAR` or `PASS_BEYOND_LINEAR` permits planning R2.

A transformation-only dissociation is the strongest result and should become the headline if it occurs.

A joint transition+state recurrence result still permits R2, but the claim must be narrowed to recurring resting-state dynamics rather than recurrence of transformation without recurrence of state.

An EC `FAIL` blocks R2 regardless of EO.

## Implementation boundaries

The implementation should add a new LEMON dataset adapter and a new R1 experiment/CLI path while reusing existing feature, receipt, permutation-p, and phase-surrogate machinery where scientifically equivalent.

No real LEMON data should be committed. Canonical receipts should contain configuration fingerprints, code version, deterministic split, per-subject summaries, population null summaries, artifact diagnostics, and the explicit outcome class.

The exact implementation file layout is intentionally deferred to the implementation plan after this spec is reviewed and approved.
