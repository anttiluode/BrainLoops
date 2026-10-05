from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .nulls import phase_surrogate
from .transition_recurrence_core import (
    _transition_spectrum_from_vectors,
    fit_standardized_pca_blocks,
    lag_grid,
    max_recurrence,
    state_recurrence_spectrum,
    transition_recurrence_spectrum,
    transition_vectors,
)

RecurrenceTier = Literal[
    "NO_ROBUST_RECURRENCE",
    "LINEAR_LAG_RECURRENCE",
    "BEYOND_LINEAR_RECURRENCE",
]


@dataclass(frozen=True)
class MetricNullResult:
    real: float
    peak_lag_s: float
    order_null: np.ndarray
    phase_null: np.ndarray
    p_order: float
    p_phase: float
    positive_order: bool
    positive_phase: bool


@dataclass(frozen=True)
class SubjectConditionResult:
    transition: MetricNullResult
    state: MetricNullResult
    transition_class: RecurrenceTier
    state_class: RecurrenceTier
    interpretation: str
    transition_spectrum: np.ndarray
    state_spectrum: np.ndarray


def permutation_p_value(real: float, null: np.ndarray) -> float:
    null = np.asarray(null, dtype=float)
    if null.ndim != 1 or null.size < 1 or not np.all(np.isfinite(null)) or not np.isfinite(real):
        raise ValueError("real and null scores must be finite")
    return float((1 + int(np.sum(null >= real))) / (1 + null.size))


def positive_direction(real: float, null: np.ndarray, tol: float = 1e-12) -> bool:
    null = np.asarray(null, dtype=float)
    if null.ndim != 1 or null.size < 1 or not np.all(np.isfinite(null)) or not np.isfinite(real):
        raise ValueError("real and null scores must be finite")
    return bool(real > float(np.median(null)) + tol)


def population_rule(
    p_value: float,
    positive_fraction: float,
    alpha: float = 0.05,
    required_fraction: float = 2 / 3,
) -> bool:
    if not (0 <= p_value <= 1 and 0 <= positive_fraction <= 1):
        raise ValueError("p_value and positive_fraction must be in [0, 1]")
    return bool(p_value <= alpha and positive_fraction >= required_fraction)


def classify_recurrence_tier(order_pass: bool, phase_pass: bool) -> RecurrenceTier:
    if phase_pass and not order_pass:
        raise ValueError("phase-tier recurrence cannot pass when order tier fails")
    if phase_pass:
        return "BEYOND_LINEAR_RECURRENCE"
    if order_pass:
        return "LINEAR_LAG_RECURRENCE"
    return "NO_ROBUST_RECURRENCE"


def _tier_rank(value: str) -> int:
    mapping = {
        "NO_ROBUST_RECURRENCE": 0,
        "LINEAR_LAG_RECURRENCE": 1,
        "BEYOND_LINEAR_RECURRENCE": 2,
    }
    if value not in mapping:
        raise ValueError(f"unknown recurrence class: {value}")
    return mapping[value]


def interpret_transition_vs_state(transition_class: str, state_class: str) -> str:
    t = _tier_rank(transition_class)
    z = _tier_rank(state_class)
    if t == 0 and z == 0:
        return "NO_ROBUST_RECURRENCE"
    if t > z:
        if t == 2:
            return "TRANSFORMATION_ONLY_AT_PHASE_TIER"
        return "TRANSFORMATION_ONLY_AT_ORDER_TIER"
    if z > t:
        return "STATE_RECURRENCE_DOMINANT"
    return "JOINT_TRANSITION_AND_STATE_RECURRENCE"


def evaluate_subject_condition(
    blocks: Sequence[np.ndarray],
    n_null: int,
    seed: int,
    epoch_s: float = 0.5,
    half_window: int = 1,
) -> SubjectConditionResult:
    if n_null < 1:
        raise ValueError("n_null must be positive")
    lags_s, lag_epochs = lag_grid(epoch_s=epoch_s)
    Z_blocks = fit_standardized_pca_blocks(blocks)

    transition_spectrum = transition_recurrence_spectrum(
        Z_blocks, lag_epochs, half_window=half_window
    )
    state_spectrum = state_recurrence_spectrum(Z_blocks, lag_epochs)
    transition_real, transition_peak = max_recurrence(transition_spectrum, lags_s)
    state_real, state_peak = max_recurrence(state_spectrum, lags_s)

    rng = np.random.default_rng(seed)
    vector_blocks = tuple(transition_vectors(block, half_window=half_window) for block in Z_blocks)
    transition_order = np.empty(n_null, dtype=float)
    state_order = np.empty(n_null, dtype=float)
    transition_phase = np.empty(n_null, dtype=float)
    state_phase = np.empty(n_null, dtype=float)

    for r in range(n_null):
        permuted_vectors = tuple(
            block[rng.permutation(block.shape[0])] for block in vector_blocks
        )
        tv_spectrum = _transition_spectrum_from_vectors(permuted_vectors, lag_epochs)
        transition_order[r] = max_recurrence(tv_spectrum, lags_s)[0]

        permuted_states = tuple(
            block[rng.permutation(block.shape[0])] for block in Z_blocks
        )
        sz_spectrum = state_recurrence_spectrum(permuted_states, lag_epochs)
        state_order[r] = max_recurrence(sz_spectrum, lags_s)[0]

        surrogate_blocks = tuple(phase_surrogate(block, rng) for block in Z_blocks)
        tp_spectrum = transition_recurrence_spectrum(
            surrogate_blocks, lag_epochs, half_window=half_window
        )
        sp_spectrum = state_recurrence_spectrum(surrogate_blocks, lag_epochs)
        transition_phase[r] = max_recurrence(tp_spectrum, lags_s)[0]
        state_phase[r] = max_recurrence(sp_spectrum, lags_s)[0]

    t_p_order = permutation_p_value(transition_real, transition_order)
    t_p_phase = permutation_p_value(transition_real, transition_phase)
    z_p_order = permutation_p_value(state_real, state_order)
    z_p_phase = permutation_p_value(state_real, state_phase)

    t_pos_order = positive_direction(transition_real, transition_order)
    t_pos_phase = positive_direction(transition_real, transition_phase)
    z_pos_order = positive_direction(state_real, state_order)
    z_pos_phase = positive_direction(state_real, state_phase)

    transition_class = classify_recurrence_tier(
        t_p_order <= 0.05 and t_pos_order,
        t_p_order <= 0.05 and t_pos_order and t_p_phase <= 0.05 and t_pos_phase,
    )
    state_class = classify_recurrence_tier(
        z_p_order <= 0.05 and z_pos_order,
        z_p_order <= 0.05 and z_pos_order and z_p_phase <= 0.05 and z_pos_phase,
    )

    return SubjectConditionResult(
        transition=MetricNullResult(
            real=transition_real,
            peak_lag_s=transition_peak,
            order_null=transition_order,
            phase_null=transition_phase,
            p_order=t_p_order,
            p_phase=t_p_phase,
            positive_order=t_pos_order,
            positive_phase=t_pos_phase,
        ),
        state=MetricNullResult(
            real=state_real,
            peak_lag_s=state_peak,
            order_null=state_order,
            phase_null=state_phase,
            p_order=z_p_order,
            p_phase=z_p_phase,
            positive_order=z_pos_order,
            positive_phase=z_pos_phase,
        ),
        transition_class=transition_class,
        state_class=state_class,
        interpretation=interpret_transition_vs_state(transition_class, state_class),
        transition_spectrum=transition_spectrum,
        state_spectrum=state_spectrum,
    )
