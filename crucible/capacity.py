"""
Capacity & transaction-cost layer — a pre-verdict reality check.

A backtest edge measured at zero cost can be untradeable once you pay to trade it, and
it can die entirely at scale: the bigger your AUM, the more your own trades move the
market against you. This module haircuts a *gross* return series for cost + market
impact so the verdict can be run on net-of-cost returns, and it finds the **capacity** —
the AUM beyond which the edge no longer survives.

It is a seam, not core: it transforms returns BEFORE the verdict and never touches the
DSR / PBO math. By construction it can only make a result worse (more honest), never
better — costs are subtracted, never added back.

Beyond a return series you must supply what capacity actually depends on (you cannot talk
about capacity honestly without these):
  - turnover : per-period one-way turnover, a fraction of NAV traded. Scalar or array.
  - a CostModel: a linear cost (half-spread + commission + slippage) and a square-root
    market-impact coefficient against the liquidity (ADV) available per rebalance.

Market impact uses the standard square-root law (Almgren et al.): the cost of trading, as
a fraction of the traded notional, grows like sqrt(participation), where
participation = traded_dollars / ADV_dollars. Doubling AUM raises impact by ~sqrt(2), so
net Sharpe decays monotonically in AUM and the capacity is well defined.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from crucible.metrics import sharpe


@dataclass(frozen=True)
class CostModel:
    """Trading-cost parameters. `linear_bps` is charged per unit turnover regardless of
    size; `impact_coef`/`adv_usd` add size-dependent square-root market impact."""
    linear_bps: float                 # half-spread + commission + fixed slippage, per unit turnover
    impact_coef: float = 0.0          # square-root impact coefficient (0 -> costs are AUM-independent)
    adv_usd: float = float("inf")     # dollar liquidity available per rebalance period

    @property
    def linear(self) -> float:
        return self.linear_bps * 1e-4


def cost_drag(turnover: np.ndarray | float, model: CostModel, aum_usd: float) -> np.ndarray:
    """Per-period cost as a fraction of NAV at the given AUM:

        drag_t = turnover_t * (linear + impact_coef * sqrt(turnover_t * AUM / ADV))
    """
    tau = np.asarray(turnover, dtype=float)
    linear = tau * model.linear
    if model.impact_coef <= 0.0 or not np.isfinite(model.adv_usd) or aum_usd <= 0.0:
        return linear + np.zeros_like(tau)
    participation = np.clip(tau * aum_usd / model.adv_usd, 0.0, None)
    impact = tau * model.impact_coef * np.sqrt(participation)
    return linear + impact


def net_returns(gross: np.ndarray, turnover: np.ndarray | float, model: CostModel,
                aum_usd: float) -> np.ndarray:
    """Gross per-period returns minus the cost drag at the given AUM."""
    return np.asarray(gross, dtype=float) - cost_drag(turnover, model, aum_usd)


def net_sharpe(gross: np.ndarray, turnover: np.ndarray | float, model: CostModel,
               aum_usd: float) -> float:
    """Per-period Sharpe of the net-of-cost series at the given AUM."""
    return sharpe(net_returns(gross, turnover, model, aum_usd))


def capacity_aum(gross: np.ndarray, turnover: np.ndarray | float, model: CostModel,
                 target_sharpe: float = 0.0, *, aum_cap: float = 1e13, tol: float = 1e-3) -> float:
    """The AUM at which net per-period Sharpe falls to `target_sharpe` — the capacity.

    Returns 0.0 if costs already sink it below target at infinitesimal size (the edge is
    untradeable at any scale), or inf if scale never does (no market impact, so the net
    Sharpe is AUM-independent and stays above target — capacity is unbounded here, but
    the linear cost may still have killed the edge: check net_sharpe at AUM 0).
    """
    if net_sharpe(gross, turnover, model, 0.0) <= target_sharpe:
        return 0.0
    if model.impact_coef <= 0.0 or not np.isfinite(model.adv_usd):
        return float("inf")
    hi = max(model.adv_usd, 1.0)
    while net_sharpe(gross, turnover, model, hi) > target_sharpe:
        hi *= 2.0
        if hi > aum_cap:
            return float("inf")
    lo = 0.0
    while hi - lo > tol * max(hi, 1.0):
        mid = 0.5 * (lo + hi)
        if net_sharpe(gross, turnover, model, mid) > target_sharpe:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def capacity_curve(gross: np.ndarray, turnover: np.ndarray | float, model: CostModel,
                   aum_grid) -> list[tuple[float, float]]:
    """[(aum, net_sharpe)] across the grid — the decay curve, for inspection/plotting."""
    return [(float(a), net_sharpe(gross, turnover, model, a)) for a in aum_grid]
