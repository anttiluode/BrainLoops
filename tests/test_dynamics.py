import numpy as np

from brainloops.dynamics import fit_linear_dynamics, score_linear_dynamics, summarize_modes


def _rotation_trajectory(r=0.95, period_epochs=12, n=500):
    theta = 2 * np.pi / period_epochs
    A = r * np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    Z = np.empty((n, 2))
    Z[0] = [1.0, 0.3]
    for t in range(1, n):
        Z[t] = A @ Z[t - 1]
    return Z


def test_fit_recovers_damped_rotation_period_and_magnitude():
    Z = _rotation_trajectory()
    fit = fit_linear_dynamics(Z, ridge=1e-9)
    modes = summarize_modes(fit, epoch_s=0.5)
    oscillatory = [m for m in modes if m.period_s is not None]
    assert oscillatory
    m = oscillatory[0]
    assert np.isclose(m.magnitude, 0.95, atol=0.01)
    assert np.isclose(m.period_s, 6.0, atol=0.2)
    assert fit.train_r2 > 0.999


def test_real_decay_has_no_oscillatory_period():
    Z = np.array([[0.8**t] for t in range(100)], dtype=float)
    fit = fit_linear_dynamics(Z, ridge=1e-9)
    modes = summarize_modes(fit, epoch_s=0.5)
    assert len(modes) == 1
    assert modes[0].period_s is None
    assert modes[0].angle_rad == 0.0


def test_score_linear_dynamics_is_high_on_same_system():
    train = _rotation_trajectory(n=300)
    test = _rotation_trajectory(n=120)
    fit = fit_linear_dynamics(train, ridge=1e-9)
    assert score_linear_dynamics(fit, test) > 0.999
