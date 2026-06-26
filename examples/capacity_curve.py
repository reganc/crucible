"""Capacity / transaction-cost reality check on the real allocator edge.

The allocator's chosen strategy survives deflation at zero cost — but how much capital
can it carry before its own market impact eats the edge? This applies the capacity layer
(square-root impact) and shows the break-even AUM and the verdict at scale. Turnover and
liquidity are inputs you must supply; the two scenarios bracket a liquid, low-turnover
book against a thin, high-turnover one.

    python examples/capacity_curve.py
"""
from __future__ import annotations

from pathlib import Path

from crucible.capacity import CostModel, capacity_aum, net_returns, net_sharpe
from crucible.ingest import load_allocator
from crucible.metrics import sharpe
from crucible.verdict import assess

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "allocator_export.csv"

SCENARIOS = {
    "liquid ETF, ~20% turnover": (0.20, CostModel(linear_bps=5.0, impact_coef=0.1, adv_usd=50e9)),
    "thin / high-turnover":      (0.60, CostModel(linear_bps=15.0, impact_coef=0.3, adv_usd=2e9)),
}


def _fmt_aum(a: float) -> str:
    if a == float("inf"):
        return "unbounded"
    return f"${a / 1e9:.1f}B" if a >= 1e9 else f"${a / 1e6:.0f}M"


def main() -> int:
    trials, chosen = load_allocator(str(FIXTURE))
    v0 = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials)
    print(f"\ngross (zero-cost): per-period Sharpe {sharpe(chosen):+.3f}, "
          f"DSR {v0.deflation.deflated_sharpe:.3f}, band {v0.band.upper()}\n")

    print(f"{'scenario':<28}{'break-even AUM':>16}{'net Sharpe @ $1B':>18}")
    for label, (turnover, model) in SCENARIOS.items():
        cap = capacity_aum(chosen, turnover, model)
        print(f"{label:<28}{_fmt_aum(cap):>16}{net_sharpe(chosen, turnover, model, 1e9):>+18.3f}")

    # Where does the edge die for the liquid book? Run the full verdict at scale.
    turnover, model = SCENARIOS["liquid ETF, ~20% turnover"]
    for aum in (1e9, 1e10):
        net = net_returns(chosen, turnover, model, aum)
        v = assess(net, n_trials=trials.shape[1], trials_matrix=trials)
        print(f"\nat ${aum / 1e9:.0f}B AUM (liquid): net Sharpe {sharpe(net):+.3f}, "
              f"DSR {v.deflation.deflated_sharpe:.3f}, band {v.band.upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
