import numpy as np
import pytest

from brainloops.transition_recurrence import (
    fit_standardized_pca_blocks,
    lag_grid,
    max_recurrence,
    state_recurrence_spectrum,
    transition_recurrence_spectrum,
    transition_vectors,
)


def test_lag_grid_is_exactly_2_to_20_seconds_by_half_second():
    lags_s, lag_epochs = lag_grid(epoch_s=0.5)
    assert np.array_equal(lags_s, np.arange(2.0, 20.0 + 0.5, 0.5))
    assert np.array_equal(lag_epochs, np.arange(4, 41))


def test_lag_grid_rejects_nonrepresentable_grid():
    with pytest.raises(ValueError, match="epoch grid"):
        lag_grid(epoch_s=0.3, min_s=2.0, max_s=3.0, step_s=0.5)


def test_transition_vectors_w1_use_pre_and_post_epoch_not_center():
    Z = np.arange(20, dtype=float).reshape(10, 2)
    V = transition_vectors(Z, half_window=1)
    assert np.array_equal(V[0], Z[2] - Z[0])
    assert V.shape[0] == len(Z) - 2


def test_transition_vectors_reject_nonfinite_or_too_short():
    with pytest.raises(ValueError):
        transition_vectors(np.array([[0.0], [np.nan], [1.0]]), half_window=1)
    with pytest.raises(ValueError):
        transition_vectors(np.zeros((2, 2)), half_window=1)


def test_transition_recurrence_equal_weights_blocks_not_pairs():
    long_v = np.tile(np.array([[1.0, 0.0]]), (20, 1))
    short_v = np.array([[1.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [-1.0, 0.0]])

    def integrate_vectors(V):
        Z = np.zeros((len(V) + 2, 2), dtype=float)
        for i, v in enumerate(V):
            Z[i + 2] = Z[i] + v
        return Z

    spectrum = transition_recurrence_spectrum(
        [integrate_vectors(long_v), integrate_vectors(short_v)],
        np.array([1]),
        half_window=1,
    )
    assert spectrum.shape == (1,)
    assert spectrum[0] == pytest.approx(0.0, abs=1e-12)


def test_state_recurrence_is_negative_median_squared_distance_and_equal_block_weighted():
    block_a = np.arange(12, dtype=float)[:, None]
    block_b = (10.0 * np.arange(6, dtype=float))[:, None]
    spectrum = state_recurrence_spectrum([block_a, block_b], np.array([1]))
    assert spectrum[0] == pytest.approx(-50.5)


def test_recurrence_rejects_block_too_short_for_requested_lag():
    with pytest.raises(ValueError, match="too short"):
        state_recurrence_spectrum([np.zeros((5, 2))], np.array([5]))
    with pytest.raises(ValueError, match="too short"):
        transition_recurrence_spectrum([np.zeros((7, 2))], np.array([5]), half_window=1)


def test_fit_standardized_pca_blocks_uses_one_basis_and_preserves_boundaries():
    rng = np.random.default_rng(4)
    a = rng.normal(size=(60, 4))
    b = rng.normal(loc=1.0, size=(45, 4))
    Za, Zb = fit_standardized_pca_blocks([a, b], pca_dim=3)
    assert Za.shape == (60, 3)
    assert Zb.shape == (45, 3)
    pooled = np.vstack([Za, Zb])
    assert np.allclose(np.std(pooled, axis=0, ddof=0), 1.0, atol=1e-12)


def test_fit_standardized_pca_blocks_rejects_zero_variance_component_scale():
    a = np.ones((30, 3))
    b = np.ones((30, 3))
    with pytest.raises(ValueError, match="variance"):
        fit_standardized_pca_blocks([a, b], pca_dim=3)


def test_max_recurrence_chooses_smallest_lag_on_exact_tie():
    score, lag = max_recurrence(np.array([0.1, 0.7, 0.7]), np.array([2.0, 2.5, 3.0]))
    assert score == pytest.approx(0.7)
    assert lag == pytest.approx(2.5)


def test_degenerate_pca_rejects_before_emitting_runtime_warning():
    import warnings

    a = np.ones((30, 3))
    b = np.ones((30, 3))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match="variance"):
            fit_standardized_pca_blocks([a, b], pca_dim=3)
    assert caught == []


def _periodic_feature_blocks(n_blocks=4, n_epochs=120):
    blocks = []
    for b in range(n_blocks):
        t = np.arange(n_epochs, dtype=float)
        phase = 2 * np.pi * t / 12.0 + 0.2 * b
        rng = np.random.default_rng(100 + b)
        blocks.append(np.c_[np.cos(phase), np.sin(phase), 0.15 * rng.normal(size=n_epochs)])
    return blocks


def test_evaluate_subject_condition_uses_full_lag_scan_for_order_null():
    import brainloops.transition_recurrence as tr

    result = tr.evaluate_subject_condition(_periodic_feature_blocks(), n_null=7, seed=4)
    assert result.transition.order_null.shape == (7,)
    assert result.state.order_null.shape == (7,)
    lags_s, lag_epochs = tr.lag_grid()
    Z = tr.fit_standardized_pca_blocks(_periodic_feature_blocks())
    real_peak_i = int(np.argmax(tr.transition_recurrence_spectrum(Z, lag_epochs)))
    rng = np.random.default_rng(4)
    V = [tr.transition_vectors(block) for block in Z]
    permuted = [block[rng.permutation(len(block))] for block in V]
    null_spectrum = tr._transition_spectrum_from_vectors(permuted, lag_epochs)
    assert np.max(null_spectrum) >= null_spectrum[real_peak_i]


def test_phase_surrogate_is_called_per_block_per_replicate(monkeypatch):
    import brainloops.transition_recurrence as tr

    calls = []

    def counting_surrogate(Z, rng):
        calls.append(Z.shape)
        return Z.copy()

    monkeypatch.setattr(tr, "phase_surrogate", counting_surrogate)
    blocks = _periodic_feature_blocks(n_blocks=4)
    tr.evaluate_subject_condition(blocks, n_null=3, seed=2)
    assert len(calls) == 4 * 3
    assert all(shape[0] == 120 for shape in calls)


def test_finite_null_p_value_and_positive_direction_are_frozen():
    import brainloops.transition_recurrence as tr

    null = np.array([0.1, 0.2, 0.3, 0.4])
    assert tr.permutation_p_value(0.35, null) == pytest.approx((1 + 1) / 5)
    assert tr.positive_direction(0.26, null)
    assert not tr.positive_direction(0.25, null)


def test_recurrence_tier_and_interpretation_mapping_is_frozen():
    import brainloops.transition_recurrence as tr

    assert tr.classify_recurrence_tier(False, False) == "NO_ROBUST_RECURRENCE"
    assert tr.classify_recurrence_tier(True, False) == "LINEAR_LAG_RECURRENCE"
    assert tr.classify_recurrence_tier(True, True) == "BEYOND_LINEAR_RECURRENCE"
    with pytest.raises(ValueError):
        tr.classify_recurrence_tier(False, True)

    assert tr.interpret_transition_vs_state("LINEAR_LAG_RECURRENCE", "NO_ROBUST_RECURRENCE") == "TRANSFORMATION_ONLY_AT_ORDER_TIER"
    assert tr.interpret_transition_vs_state("BEYOND_LINEAR_RECURRENCE", "LINEAR_LAG_RECURRENCE") == "TRANSFORMATION_ONLY_AT_PHASE_TIER"
    assert tr.interpret_transition_vs_state("BEYOND_LINEAR_RECURRENCE", "BEYOND_LINEAR_RECURRENCE") == "JOINT_TRANSITION_AND_STATE_RECURRENCE"
    assert tr.interpret_transition_vs_state("NO_ROBUST_RECURRENCE", "LINEAR_LAG_RECURRENCE") == "STATE_RECURRENCE_DOMINANT"
    assert tr.interpret_transition_vs_state("NO_ROBUST_RECURRENCE", "NO_ROBUST_RECURRENCE") == "NO_ROBUST_RECURRENCE"


def test_population_rule_requires_p_and_two_thirds_direction():
    import brainloops.transition_recurrence as tr

    assert tr.population_rule(0.05, 2 / 3)
    assert not tr.population_rule(0.06, 1.0)
    assert not tr.population_rule(0.01, 0.65)
