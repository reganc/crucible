"""Tests for PBO/CSCV and the end-to-end verdict."""
from __future__ import annotations

import numpy as np

from crucible.metrics import sharpe
from crucible.pbo import pbo_cscv
from crucible.verdict import assess


def _noise_matrix(T=600, N=40, seed=11):
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 0.01, size=(T, N))


def _real_matrix(T=600, N=40, seed=11):
    M = _noise_matrix(T, N, seed)
    rng = np.random.default_rng(seed + 1)
    M[:, 0] = rng.normal(0.002, 0.01, size=T)  # one unambiguously real edge (~3 ann. Sharpe)
    return M


def test_pbo_valid_and_noise_higher_than_real_edge():
    Mn, Mr = _noise_matrix(), _real_matrix()
    pn = pbo_cscv(Mn, n_groups=10)
    pr = pbo_cscv(Mr, n_groups=10)
    assert pn.n_combinations == 252           # C(10,5)
    assert 0.0 <= pn.pbo <= 1.0 and 0.0 <= pr.pbo <= 1.0
    # a matrix containing a genuine, dominant edge overfits less than pure noise
    assert pr.pbo < pn.pbo


def test_verdict_flags_noise_red():
    M = _noise_matrix()
    chosen = M[:, int(np.argmax([sharpe(M[:, j]) for j in range(M.shape[1])]))]
    v = assess(chosen, n_trials=M.shape[1], trials_matrix=M, pbo_groups=10)
    assert v.band == "red"
    assert v.deflation.deflated_sharpe < 0.95


def test_verdict_treats_real_edge_better_than_noise():
    Mn, Mr = _noise_matrix(), _real_matrix()
    cn = Mn[:, int(np.argmax([sharpe(Mn[:, j]) for j in range(Mn.shape[1])]))]
    cr = Mr[:, 0]
    vn = assess(cn, n_trials=Mn.shape[1], trials_matrix=Mn, pbo_groups=10)
    vr = assess(cr, n_trials=Mr.shape[1], trials_matrix=Mr, pbo_groups=10)
    assert vr.deflation.deflated_sharpe > vn.deflation.deflated_sharpe
    assert vr.band != "red"   # a genuine strong edge must not be flagged overfit
