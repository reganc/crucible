"""Capacity / transaction-cost layer — costs only ever make the verdict worse, and
square-root market impact gives a well-defined capacity (the AUM where the edge dies)."""
from __future__ import annotations

import numpy as np

from crucible.capacity import CostModel, capacity_aum, cost_drag, net_returns, net_sharpe
from crucible.metrics import sharpe


def _gross(seed: int = 0, n: int = 600) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.002, 0.01, n)


def test_zero_cost_is_identity():
    g = _gross()
    free = CostModel(linear_bps=0.0)                       # no linear, no impact
    assert np.allclose(net_returns(g, 0.3, free, 1e9), g)
    assert net_sharpe(g, 0.3, free, 1e9) == sharpe(g)


def test_costs_never_improve_sharpe():
    g = _gross()
    m = CostModel(linear_bps=10.0, impact_coef=0.2, adv_usd=1e9)
    gs = sharpe(g)
    for aum in (0.0, 1e8, 1e9, 1e10):
        assert net_sharpe(g, 0.3, m, aum) <= gs + 1e-12   # can only subtract, never flatter


def test_net_sharpe_monotonic_decreasing_in_aum():
    g = _gross()
    m = CostModel(linear_bps=5.0, impact_coef=0.2, adv_usd=1e9)
    s = [net_sharpe(g, 0.3, m, a) for a in (0.0, 1e8, 1e9, 5e9, 2e10)]
    assert all(s[i] > s[i + 1] for i in range(len(s) - 1))


def test_capacity_is_finite_and_crosses_target():
    g = _gross()
    m = CostModel(linear_bps=5.0, impact_coef=0.2, adv_usd=1e9)
    cap = capacity_aum(g, 0.3, m)
    assert 0.0 < cap < float("inf")
    assert abs(net_sharpe(g, 0.3, m, cap)) < 0.01         # net Sharpe ~ 0 at capacity


def test_no_impact_means_unbounded_capacity():
    g = _gross()
    flat = CostModel(linear_bps=5.0)                       # AUM-independent (no impact)
    assert capacity_aum(g, 0.3, flat) == float("inf")


def test_costs_can_kill_edge_at_any_size():
    g = _gross()
    brutal = CostModel(linear_bps=10_000.0)               # 100%/unit-turnover -> dead at AUM 0
    assert capacity_aum(g, 1.0, brutal) == 0.0


def test_capacity_falls_with_turnover_and_rises_with_liquidity():
    g = _gross()
    base = CostModel(linear_bps=5.0, impact_coef=0.2, adv_usd=1e9)
    deep = CostModel(linear_bps=5.0, impact_coef=0.2, adv_usd=4e9)
    assert capacity_aum(g, 0.6, base) < capacity_aum(g, 0.2, base)   # more turnover -> less capacity
    assert capacity_aum(g, 0.3, deep) > capacity_aum(g, 0.3, base)   # more liquidity -> more capacity


def test_market_impact_follows_square_root_law():
    m = CostModel(linear_bps=0.0, impact_coef=0.3, adv_usd=1e9)      # impact only
    assert np.isclose(cost_drag(0.25, m, 4e9) / cost_drag(0.25, m, 1e9), 2.0)   # 4x AUM -> 2x impact
