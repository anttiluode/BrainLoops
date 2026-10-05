# Temporal lenses, resonance valves, and the BrainLoops evidence

Date: 5 October 2026. This note records the discussion and source/result audit;
it does not change a frozen gate or report a new biological experiment.

## The hypothesis that survives

Activity-dependent inhibition may regulate which recurrent histories can amplify.
The same controller could affect memory duration, contextual sensitivity, and
stability. A temporal "lens" and a resonance "valve" could therefore describe
different effects of one control operation.

BrainLoops has not identified that controller in EEG. The measured finding is
repeated event-aligned transition direction. Connecting it to Martinotti cells,
a reset, or seizure prevention remains a hypothesis.

## Biological grounding and limits

Silberberg and Markram found facilitating pyramidal-to-Martinotti connections and
Martinotti-mediated inhibition of neighboring pyramidal dendrites that increases
with presynaptic firing rate and duration. Murayama and colleagues showed that
dendritic inhibition controls sensory-response gain and can block dendritic
calcium spikes. Those findings support activity-dependent control of dendritic
amplification with computational consequences.

The role is not simply to remove synchrony. Berger and colleagues found that
Martinotti-mediated inhibition can correlate membrane fluctuations and synchronize
subsequent pyramidal spiking. Organizing timing and limiting amplification can
coexist.

Epilepsy links are conditional. Tai and colleagues found impaired SST and PV
interneuron excitability in a Dravet mouse model. Miri and colleagues found that
inhibition remained effective before seizure onset in their acute models.
Magloire and colleagues demonstrated a timing-dependent switch from anti-ictal to
pro-ictal effects of PV stimulation involving chloride regulation; the
dendrite-targeting SOM population did not share that switch in their experiment.
These studies do not establish a universal "more inhibition means safer" rule or
an evolutionary explanation for apical tufts.

## Memory and amplification share dynamics

One proposed abstraction is

$$
s_{t+1}=A(g_t)s_t+B x_t,\qquad
g_{t+1}=F(g_t,\text{recent activity}).
$$

Here the state is $s$ and the feedback variable $g$ changes effective coupling or
dendritic gain. For a local linear mode with eigenvalue
$\lambda_k=r_k e^{i\omega_k}$, its contribution after $L$ steps scales as
$r_k^L e^{i\omega_k L}$. Magnitude affects persistence/amplification and phase
affects timing. In a fixed single mode, $r<1$ decays and $r>1$ amplifies; delays,
nonlinearities, changing couplings, and transient amplification make network
stability more demanding than this scalar test.

This provides a precise connection between temporal memory and regulation. A
controller that changes which modes persist also changes what past inputs remain
available and how strongly new context can amplify them. It need not have only a
memory role or only a protective role.

A loop alone does not create separately addressable copies of the past:

$$
s_t=u_t+a s_{t-d}=\sum_{n\ge0}a^n u_{t-nd}.
$$

Returning contributions are still summed in the observed coordinate. A physical
delay buffer or distinguishable recurrent modes add coordinates; their ability to
retain different histories must be checked through impulse-response directions,
rank, conditioning, and noise robustness. An invertible change/residual basis can
expose retained distinctions, but cannot recover information already discarded.

## What Gate 1C measures

The EEG experiment is in BrainLoops; MultipleTemporalLenses is the synthetic
compact-memory project.

The recovered full Gate 1C receipt contains 109 subjects, with 21 development and
88 held out, and 1,308 successful runs with none skipped. Its 5,245,933 bytes have
SHA-256 `b3be8457075207b30978bd7c057a6197df1af2ff935970c7cdb84c87058e508b`, exactly
matching the previously committed summary. All 22 audited hash/count/numerical
summary fields were recomputed without a mismatch.

| Held-out quantity | Value |
|---|---:|
| Median transition-consistency score | 0.0526472049 |
| Median aggregate null score | 0.0059305559 |
| Aggregate permutation p | 0.01, the 99-null resolution floor |
| Subjects in the positive direction | 78 / 88 |
| Median preceding-task history diagnostic | -0.0111547621 |
| Subjects with positive history diagnostic | 31 / 88 |

Gate 1B failed its same-coarse-state-return criterion. Gate 1C, designed afterward
on the same dataset, supports repeated direction of change at T0. It is not an
independent replication, and its preceding-T1/T2 diagnostic did not support the
specific coarse-history effect.

Features are 0.5-second band-power epochs followed by robust scaling and PCA.
With half-window 1, the transition subtracts epoch $t-1$ from epoch $t+1$ and
excludes the onset epoch. The primary score normalizes transition vectors before
comparing their directions. It measures neither millisecond synaptic timing nor
reduced firing, excitation, physical energy, or state magnitude.

A concrete counterexample using the actual committed scoring function:

```python
import numpy as np
from experiments.gate1c_eegmmidb import transition_consistency_score

z = np.column_stack((np.linspace(0.0, 5.0, 60), np.zeros(60)))
events = np.array([5, 15, 25, 35, 45, 55])
score = transition_consistency_score(z, events, half_window=1)
assert np.isclose(score, 1.0)
assert np.linalg.norm(z[-1]) > np.linalg.norm(z[0])
```

The trajectory continually increases and never returns to a previous state.
Identical transition directions still produce a perfect score. This is a
counterexample to equating the score itself with a reset, not a claim that this
trajectory passes the full event-alignment permutation gate.

A motor-task-related ERD/ERS response, including beta rebound, is a plausible
explanation of the cue alignment. The gate does not isolate beta or motor
channels, so that attribution is untested. Gaetz and colleagues found an
association between GABA concentration and motor beta rebound. Sherman and
colleagues offered an account of spontaneous beta events involving coordinated
excitatory input to proximal and distal dendrites. That does not settle the cause
of post-movement rebound, but beta power is not a unique Martinotti fingerprint.

## Related memory-test correction

The audited MultipleTemporalLenses Gate 3 discards candidate roles: ordered pair
(A, B) and ordered pair (B, A) both become the same mixture $0.5A+0.5B$, while the
same context bit demands different labels. Under the intended uniform generator,
60 latent pair/context cases collapse to 30 observable inputs, each with two
equally likely answers. The expected Bayes accuracy ceiling is 50%, below the
gate's required 80%.

This is an invalid test of later reinterpretation, rather than a demonstrated
architectural failure. Other gates ask different questions. Preserve roles through
tagged inputs or distinct positions and establish an explicit-history oracle
before judging compact memory. This note records that cross-project limitation;
the task generator lives in
[MultipleTemporalLenses](https://github.com/anttiluode/MultipleTemporalLenses/blob/de74308099ffc4d0e20370cea9dfdf930a911ffb/src/multiple_temporal_lenses/tasks.py).

Tupsu tests burst-dependent episode compression. Its reported boundary-selection
comparison does not isolate stabilization of a recurrent excitatory population,
so it cannot by itself assign inhibition a primarily protective biological role.

## Next informative tests

For the valve hypothesis, compare a recurrent excitatory/inhibitory simulation
with no adaptive feedback, fixed damping, activity-dependent feedback, and
timing-shuffled feedback matched in average strength. Match memory capacity,
readout, training budget, and total inhibitory cost. Measure both lag-dependent
recall and stability under distractors or sustained input: amplification,
saturation, recovery time, and response to a controlled probe.

The informative outcome would be useful retained history across a wider input or
gain range than fixed damping at the same cost, with a loss under timing
shuffling. Merely erasing history to stabilize the system would not meet the
joint goal. This is a proposed experiment, not implemented BrainLoops evidence.

For EEG, separate channel/band contributions and use independent resting data
with frozen preprocessing and appropriate spectral nulls. R1 implements a
within-rest transition/state recurrence comparison; it does not yet demonstrate
transfer of a frozen task-derived T0 template. Even finding recurring task-like
motifs at rest would not identify their cell type or protective function.
Anti-seizure causality needs additional circuit-resolved or causal evidence.

## Primary references

- Silberberg & Markram (2007), [Disynaptic inhibition between neocortical pyramidal cells mediated by Martinotti cells](https://doi.org/10.1016/j.neuron.2007.02.012).
- Murayama et al. (2009), [Dendritic encoding of sensory stimuli controlled by deep cortical interneurons](https://doi.org/10.1038/nature07663).
- Berger et al. (2010), [Brief Bursts Self-Inhibit and Correlate the Pyramidal Network](https://doi.org/10.1371/journal.pbio.1000473).
- Tai et al. (2014), [Impaired excitability of somatostatin- and parvalbumin-expressing cortical interneurons in a mouse model of Dravet syndrome](https://doi.org/10.1073/pnas.1411131111).
- Miri et al. (2018), [Altered hippocampal interneuron activity precedes ictal onset](https://doi.org/10.7554/eLife.40750).
- Magloire et al. (2019), [KCC2 overexpression prevents the paradoxical seizure-promoting action of somatic inhibition](https://doi.org/10.1038/s41467-019-08933-4).
- Gaetz et al. (2011), [Relating MEG measured motor cortical oscillations to resting GABA concentration](https://doi.org/10.1016/j.neuroimage.2010.12.077).
- Sherman et al. (2016), [Neural mechanisms of transient neocortical beta rhythms](https://doi.org/10.1073/pnas.1604135113).
