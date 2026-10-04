import numpy as np

from brainloops.nulls import phase_surrogate, reversible_markov_samples


def test_reversible_null_is_finite_for_sparse_graph_with_unused_state():
    N = np.array([[0, 50, 0], [50, 0, 0], [0, 0, 0]], dtype=float)
    vals = reversible_markov_samples(N, n_steps=200, n_null=50, rng=np.random.default_rng(0))
    assert vals.shape == (50,)
    assert np.all(np.isfinite(vals))
    assert np.mean(vals) < 0.2


def test_reversible_null_handles_empty_graph():
    vals = reversible_markov_samples(np.zeros((3, 3)), n_steps=10, n_null=5, rng=np.random.default_rng(0))
    assert np.array_equal(vals, np.zeros(5))


def test_phase_surrogate_preserves_power_and_cross_spectral_phase():
    rng = np.random.default_rng(4)
    t = np.arange(512)
    z0 = np.sin(2 * np.pi * t / 32) + 0.2 * rng.normal(size=t.size)
    z1 = np.cos(2 * np.pi * t / 32) + 0.2 * rng.normal(size=t.size)
    Z = np.c_[z0, z1]
    S = phase_surrogate(Z, np.random.default_rng(5))

    F = np.fft.rfft(Z, axis=0)
    G = np.fft.rfft(S, axis=0)
    assert np.allclose(np.abs(F), np.abs(G), atol=1e-10)
    cross_F = F[:, 0] * np.conj(F[:, 1])
    cross_G = G[:, 0] * np.conj(G[:, 1])
    mask = np.abs(cross_F) > 1e-8
    assert np.allclose(np.angle(cross_F[mask]), np.angle(cross_G[mask]), atol=1e-10)
    assert not np.allclose(Z, S)

class _CountingRng:
    def __init__(self, seed=0):
        self.inner = np.random.default_rng(seed)
        self.choice_calls = 0

    def choice(self, *args, **kwargs):
        self.choice_calls += 1
        return self.inner.choice(*args, **kwargs)

    def random(self, *args, **kwargs):
        return self.inner.random(*args, **kwargs)


def test_reversible_null_does_not_use_categorical_choice_per_transition():
    N = np.array([[0, 25, 10], [25, 0, 15], [10, 15, 0]], dtype=float)
    rng = _CountingRng(0)
    vals = reversible_markov_samples(N, n_steps=500, n_null=7, rng=rng)
    assert vals.shape == (7,)
    assert rng.choice_calls <= 7
