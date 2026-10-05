import numpy as np

from brainloops.transition_recurrence import evaluate_subject_condition, population_rule
from experiments.r1_synthetic import synthetic_cases, run_r1_synthetic


def test_r1_synthetic_semantic_cases_have_frozen_outcomes():
    receipt = run_r1_synthetic(seed=1, n_null=19)
    assert receipt["status"] == "PASS"
    cases = receipt["cases"]
    assert cases["iid_noise"]["transition_class"] == "NO_ROBUST_RECURRENCE"
    assert cases["linear_rotation"]["transition_class"] == "LINEAR_LAG_RECURRENCE"
    assert cases["drifting_repeated_transform"]["transition_class"] in {
        "LINEAR_LAG_RECURRENCE", "BEYOND_LINEAR_RECURRENCE"
    }
    assert cases["drifting_repeated_transform"]["interpretation"].startswith("TRANSFORMATION_ONLY")
    rank = {"NO_ROBUST_RECURRENCE": 0, "LINEAR_LAG_RECURRENCE": 1, "BEYOND_LINEAR_RECURRENCE": 2}
    assert rank[cases["state_return_variable_direction"]["state_class"]] > rank[cases["state_return_variable_direction"]["transition_class"]]
    assert cases["state_return_variable_direction"]["interpretation"] == "STATE_RECURRENCE_DOMINANT"


def test_r1_synthetic_receipt_records_config_and_code_version():
    receipt = run_r1_synthetic(seed=2, n_null=19)
    assert receipt["gate"] == "r1_synthetic"
    assert receipt["config"]["n_null"] == 19
    assert receipt["config"]["seed"] == 2
    assert receipt["config"]["code_version"]
    assert len(receipt["config_fingerprint"]) == 64


def test_max_statistic_null_pass_rate_is_not_inflated():
    from brainloops.transition_recurrence import (
        _transition_spectrum_from_vectors,
        lag_grid,
        max_recurrence,
        permutation_p_value,
        positive_direction,
    )

    lags_s, lag_epochs = lag_grid()
    passes = 0
    for subject in range(100):
        rng = np.random.default_rng(1000 + subject)
        vectors = [rng.normal(size=(178, 4)) for _ in range(4)]
        real = max_recurrence(_transition_spectrum_from_vectors(vectors, lag_epochs), lags_s)[0]
        null = np.empty(19, dtype=float)
        for r in range(19):
            permuted = [v[rng.permutation(len(v))] for v in vectors]
            spectrum = _transition_spectrum_from_vectors(permuted, lag_epochs)
            null[r] = max_recurrence(spectrum, lags_s)[0]
        if permutation_p_value(real, null) <= 0.05 and positive_direction(real, null):
            passes += 1
    assert passes <= 10
