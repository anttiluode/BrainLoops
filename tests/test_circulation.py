import numpy as np

from brainloops.circulation import (
    asymmetry_index,
    return_times,
    top_three_cycles,
    transition_counts,
)
from brainloops.states import collapse_visits, fit_states


def test_collapse_visits_removes_dwell_and_keeps_epoch_starts():
    labels = np.array([0, 0, 0, 1, 1, 2, 0])
    visits = collapse_visits(labels)
    assert visits.labels.tolist() == [0, 1, 2, 0]
    assert visits.starts.tolist() == [0, 3, 5, 6]


def test_dwell_does_not_enter_transition_flux():
    visits = collapse_visits(np.array([0, 0, 0, 1, 1, 0]))
    N = transition_counts(visits.labels, 2)
    assert N.tolist() == [[0.0, 1.0], [1.0, 0.0]]
    assert asymmetry_index(N) == 0.0


def test_return_times_exclude_immediate_dwell_repeats():
    labels = np.array([0, 0, 1, 1, 0, 2, 0])
    rt = return_times(labels, epoch_s=0.5)
    assert sorted(rt.tolist()) == [1.0, 1.5]


def test_top_three_cycles_finds_repeated_oriented_rounds():
    labels = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0])
    visits = collapse_visits(labels)
    N = transition_counts(visits.labels, 3)
    cycles = top_three_cycles(N, visits, epoch_s=0.5, n=1)
    assert cycles[0].cycle == (0, 1, 2)
    assert cycles[0].net_flux > 0
    assert cycles[0].full_rounds == 3
    assert cycles[0].period_s == 1.5


def test_fit_states_returns_one_label_per_epoch():
    rng = np.random.default_rng(0)
    Z = np.r_[rng.normal(-2, 0.1, size=(20, 2)), rng.normal(2, 0.1, size=(20, 2))]
    part = fit_states(Z, k=2, seed=0)
    assert part.labels.shape == (40,)
    assert part.centers.shape == (2, 2)
    assert part.k == 2
