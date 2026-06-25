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


class PrecomputedRegime:
    """A `RegimeClassifier` whose per-observation labels are already aligned to the
    target return series.

    The Protocol's `label(returns)` takes only values, but real classifiers (the
    Schwab macro brain) are keyed by date and don't consume a returns array. So the
    date-join happens in the ingest seam, and its result — one integer regime per
    observation — is carried here. Engine-agnostic by construction: the verdict only
    ever sees integer labels, never the external regime schema.
    """

    def __init__(self, labels: np.ndarray):
        self._labels = np.asarray(labels, dtype=int)
        self.n_regimes = int(np.unique(self._labels).size)

    def label(self, returns: np.ndarray) -> np.ndarray:
        if len(returns) != len(self._labels):
            raise ValueError(
                f"PrecomputedRegime holds {len(self._labels)} labels but got "
                f"{len(returns)} observations — align the labels to the return series first."
            )
        return self._labels


def regime_conditional_sharpe(returns: np.ndarray, labels: np.ndarray) -> dict[int, float]:
    """Per-regime per-period Sharpe — surfaces single-regime dependence at a glance."""
    from crucible.metrics import sharpe
    out: dict[int, float] = {}
    for r in np.unique(labels):
        mask = labels == r
        if mask.sum() >= 2:
            out[int(r)] = sharpe(np.asarray(returns)[mask])
    return out


def regime_contributions(returns: np.ndarray, labels: np.ndarray) -> dict[int, float]:
    """Total summed return contributed by each regime — its share of cumulative
    performance. The dominant regime is the one that carried the edge."""
    r = np.asarray(returns, dtype=float)
    lab = np.asarray(labels)
    return {int(g): float(r[lab == g].sum()) for g in np.unique(lab)}


def dominant_regime(returns: np.ndarray, labels: np.ndarray) -> int | None:
    """The regime contributing the most positive performance (largest summed return)
    — the regime the edge was 'born in'. None if fewer than 2 regimes are present."""
    contrib = regime_contributions(returns, labels)
    if len(contrib) < 2:
        return None
    return max(contrib, key=contrib.__getitem__)
