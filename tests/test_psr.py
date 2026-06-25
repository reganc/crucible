"""Tests for the deflation math (PSR / DSR / minTRL)."""
from __future__ import annotations

import numpy as np

from crucible.metrics import sharpe, skew, kurtosis
from crucible.psr import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    min_track_record_length,
    probabilistic_sharpe_ratio,
)


def test_psr_strong_edge_near_one():
    rng = np.random.default_rng(1)
    r = rng.normal(0.001, 0.005, size=2000)  # strong, long track record
    psr = probabilistic_sharpe_ratio(sharpe(r), len(r), skew(r), kurtosis(r))
    assert psr > 0.99


def test_psr_weak_edge_uncertain():
    rng = np.random.default_rng(2)
    r = rng.normal(0.0001, 0.01, size=60)  # tiny edge, short sample
    psr = probabilistic_sharpe_ratio(sharpe(r), len(r), skew(r), kurtosis(r))
    assert 0.2 < psr < 0.9


def test_expected_max_sharpe_grows_with_trials():
    v = 0.04  # variance of trial Sharpes
    assert expected_max_sharpe(v, 1) == 0.0
    assert expected_max_sharpe(v, 10) < expected_max_sharpe(v, 1000)


def test_deflation_penalizes_many_trials():
    rng = np.random.default_rng(3)
    r = rng.normal(0.0004, 0.01, size=1000)
    s, n, sk, ku = sharpe(r), len(r), skew(r), kurtosis(r)
    dsr_few = deflated_sharpe_ratio(s, n, sk, ku, sr_variance=0.02, n_trials=5)
    dsr_many = deflated_sharpe_ratio(s, n, sk, ku, sr_variance=0.02, n_trials=5000)
    assert dsr_many < dsr_few  # more trials -> harder to clear


def test_min_trl_infinite_when_no_edge():
    rng = np.random.default_rng(4)
    r = rng.normal(0.0, 0.01, size=500)
    # near-zero Sharpe -> need effectively infinite data to prove an edge vs 0
    mtrl = min_track_record_length(max(sharpe(r), 0.0), skew(r), kurtosis(r))
    assert mtrl > 100 or mtrl == float("inf")
