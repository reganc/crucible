"""Task 2 — regime-conditional deflation.

Synthetic, hermetic cases (no allocator dependency): an edge that lives entirely in one
regime must show a large Deflated-Sharpe drop and trigger the regime-captive note; a
regime-robust edge must not. Plus the gating and the generic carrier's contract.
"""
from __future__ import annotations

import numpy as np

from crucible.regime import (
    PrecomputedRegime,
    SingleRegime,
    dominant_regime,
    regime_contributions,
)
from crucible.verdict import REGIME_COLLAPSE_DROP, assess


def _split_labels(t: int) -> np.ndarray:
    labels = np.zeros(t, dtype=int)
    labels[t // 2:] = 1
    return labels


def test_edge_in_one_regime_collapses():
    rng = np.random.default_rng(0)
    t = 300
    labels = _split_labels(t)
    r = np.empty(t)
    r[labels == 0] = rng.normal(0.006, 0.008, (labels == 0).sum())   # regime 0: real edge
    r[labels == 1] = rng.normal(0.0, 0.008, (labels == 1).sum())     # regime 1: pure noise

    v = assess(r, n_trials=5, sr_variance=0.01, regime=PrecomputedRegime(labels))

    assert v.regime_deflation is not None
    rd = v.regime_deflation
    assert rd.dominant_regime == 0                       # the edge's home regime
    assert rd.drop >= REGIME_COLLAPSE_DROP               # large DSR drop
    assert rd.dsr_ex_dominant < rd.dsr_full
    assert rd.regime_captive
    assert any("regime-captive" in n for n in v.notes)


def test_regime_robust_edge_does_not_collapse():
    rng = np.random.default_rng(1)
    t = 400
    labels = _split_labels(t)
    r = rng.normal(0.005, 0.008, t)                      # same edge in BOTH regimes

    v = assess(r, n_trials=5, sr_variance=0.01, regime=PrecomputedRegime(labels))

    assert v.regime_deflation is not None
    rd = v.regime_deflation
    assert rd.drop < REGIME_COLLAPSE_DROP                # edge survives removal
    assert not rd.regime_captive
    assert not any("regime-captive" in n for n in v.notes)


def test_no_regime_deflation_without_real_classifier():
    rng = np.random.default_rng(2)
    r = rng.normal(0.004, 0.01, 200)
    # SingleRegime fallback -> one regime -> feature gated off
    assert assess(r, n_trials=5, sr_variance=0.01, regime=SingleRegime()).regime_deflation is None
    # No classifier at all -> also off
    assert assess(r, n_trials=5, sr_variance=0.01).regime_deflation is None
    # A real classifier but only one regime present -> off
    one = PrecomputedRegime(np.zeros(200, dtype=int))
    assert assess(r, n_trials=5, sr_variance=0.01, regime=one).regime_deflation is None


def test_dominant_regime_and_contributions():
    r = np.array([0.1, 0.1, -0.01, -0.01])
    labels = np.array([0, 0, 1, 1])
    contrib = regime_contributions(r, labels)
    assert contrib[0] > contrib[1]
    assert dominant_regime(r, labels) == 0
    assert dominant_regime(r, np.zeros(4, dtype=int)) is None   # <2 regimes


def test_precomputed_regime_length_mismatch_raises():
    clf = PrecomputedRegime(np.array([0, 1, 0]))
    try:
        clf.label(np.zeros(5))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on length mismatch")
