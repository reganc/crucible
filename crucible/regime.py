"""
Regime seam.

CRUCIBLE's honesty layer is regime-aware by design: a strategy can be "real" overall but
driven entirely by one regime. This Protocol is where the six-regime portfolio brain
(Kelly sizing, ATR adaptive bands, regime classifier) plugs in to (a) label each
observation with its regime and (b) enable regime-conditional DSR/PBO — answering "does
the edge survive when you remove the regime it was born in?"

Phase 0 ships a trivial single-regime classifier so the pipeline runs; swap in the real
classifier here.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class RegimeClassifier(Protocol):
    n_regimes: int
    def label(self, returns: np.ndarray) -> np.ndarray:
        """Return an integer regime label per observation (length T)."""
        ...


class SingleRegime:
    """Trivial stub — everything is regime 0. Replace with the six-regime brain."""
    n_regimes = 1

    def label(self, returns: np.ndarray) -> np.ndarray:
        return np.zeros(len(returns), dtype=int)


def regime_conditional_sharpe(returns: np.ndarray, labels: np.ndarray) -> dict[int, float]:
    """Per-regime per-period Sharpe — surfaces single-regime dependence at a glance."""
    from crucible.metrics import sharpe
    out: dict[int, float] = {}
    for r in np.unique(labels):
        mask = labels == r
        if mask.sum() >= 2:
            out[int(r)] = sharpe(np.asarray(returns)[mask])
    return out
