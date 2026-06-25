"""
Return metrics — the per-period Sharpe and higher moments that the deflation math
consumes. Everything here is per-period (not annualized) unless explicitly noted,
because PSR/DSR are defined on per-period Sharpe + the sample's skew/kurtosis.
"""
from __future__ import annotations

import numpy as np


def sharpe(returns: np.ndarray, rf: float = 0.0) -> float:
    """Per-period Sharpe ratio (no annualization)."""
    r = np.asarray(returns, dtype=float) - rf
    sd = r.std(ddof=1)
    return 0.0 if sd == 0 else r.mean() / sd


def annualized_sharpe(returns: np.ndarray, periods_per_year: int = 252, rf: float = 0.0) -> float:
    return sharpe(returns, rf) * np.sqrt(periods_per_year)


def skew(returns: np.ndarray) -> float:
    """Sample skewness (Fisher, biased estimator as used in the DSR papers)."""
    r = np.asarray(returns, dtype=float)
    n = r.size
    if n < 3:
        return 0.0
    m = r.mean()
    s = r.std(ddof=0)
    return 0.0 if s == 0 else float(np.mean(((r - m) / s) ** 3))


def kurtosis(returns: np.ndarray) -> float:
    """Non-excess (normal == 3.0) kurtosis, matching the DSR formulation."""
    r = np.asarray(returns, dtype=float)
    n = r.size
    if n < 4:
        return 3.0
    m = r.mean()
    s = r.std(ddof=0)
    return 3.0 if s == 0 else float(np.mean(((r - m) / s) ** 4))


def moments(returns: np.ndarray) -> dict:
    return {
        "n": int(np.asarray(returns).size),
        "sharpe": sharpe(returns),
        "skew": skew(returns),
        "kurtosis": kurtosis(returns),
    }
