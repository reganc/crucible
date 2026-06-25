"""
Probabilistic Sharpe Ratio (PSR), Deflated Sharpe Ratio (DSR), and Minimum Track
Record Length (minTRL).

References:
  Bailey & López de Prado (2012), "The Sharpe Ratio Efficient Frontier" — PSR, minTRL.
  Bailey & López de Prado (2014), "The Deflated Sharpe Ratio" — DSR, expected max SR.

All Sharpe inputs are PER-PERIOD (not annualized). The whole point of this module is
to answer: given how many strategy variants you tried, is this Sharpe distinguishable
from the best you'd expect from luck alone?
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

EULER_MASCHERONI = 0.5772156649015329


def probabilistic_sharpe_ratio(sr: float, n: int, skew: float, kurtosis: float,
                               sr_benchmark: float = 0.0) -> float:
    """PSR: probability that the true (per-period) Sharpe exceeds `sr_benchmark`,
    correcting for sample length and non-normality (skew/kurtosis).

    kurtosis is non-excess (normal == 3.0).
    """
    if n < 2:
        return float("nan")
    denom = np.sqrt(1.0 - skew * sr + ((kurtosis - 1.0) / 4.0) * sr**2)
    if denom == 0 or not np.isfinite(denom):
        return float("nan")
    z = (sr - sr_benchmark) * np.sqrt(n - 1) / denom
    return float(norm.cdf(z))


def expected_max_sharpe(sr_variance: float, n_trials: int) -> float:
    """Expected maximum of N independent Sharpe ratios drawn from a distribution with
    variance `sr_variance` and mean 0 — the deflation benchmark. This is what the best
    of N noise trials would score on average.
    """
    if n_trials < 1 or sr_variance <= 0:
        return 0.0
    if n_trials == 1:
        return 0.0
    e = np.e
    gamma = EULER_MASCHERONI
    # Bailey & López de Prado (2014), eq. for E[max SR]
    term = ((1 - gamma) * norm.ppf(1.0 - 1.0 / n_trials)
            + gamma * norm.ppf(1.0 - 1.0 / (n_trials * e)))
    return float(np.sqrt(sr_variance) * term)


def deflated_sharpe_ratio(sr: float, n: int, skew: float, kurtosis: float,
                          sr_variance: float, n_trials: int) -> float:
    """DSR = PSR evaluated against the expected-maximum-Sharpe benchmark for N trials.

    sr_variance: variance of the Sharpe ratios across all trials you ran.
    n_trials:    how many strategy variants/configs you tried (the multiple-testing count).

    DSR < 0.95 (say) means: after accounting for how many things you tried, this edge is
    NOT convincingly better than the best you'd expect from luck.
    """
    sr0 = expected_max_sharpe(sr_variance, n_trials)
    return probabilistic_sharpe_ratio(sr, n, skew, kurtosis, sr_benchmark=sr0)


def min_track_record_length(sr: float, skew: float, kurtosis: float,
                            sr_benchmark: float = 0.0, confidence: float = 0.95) -> float:
    """minTRL: how many observations you'd need for PSR(sr_benchmark) to reach `confidence`.

    If your actual track record is shorter than this, you don't yet have enough data to
    claim the edge at the requested confidence.
    """
    if sr <= sr_benchmark:
        return float("inf")
    denom = (sr - sr_benchmark) ** 2
    z = norm.ppf(confidence)
    return float(1.0 + (1.0 - skew * sr + ((kurtosis - 1.0) / 4.0) * sr**2) * (z**2) / denom)


@dataclass(slots=True)
class DeflationReport:
    observed_sharpe: float          # per-period
    n_obs: int
    n_trials: int
    sr_benchmark: float             # expected max SR from N trials of noise
    psr_vs_zero: float
    deflated_sharpe: float
    min_trl: float
    skew: float
    kurtosis: float

    @property
    def passes(self) -> bool:
        return self.deflated_sharpe >= 0.95 and self.n_obs >= self.min_trl
