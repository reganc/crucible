"""Generate a real allocator trial export for CRUCIBLE's ingest adapter.

The honest multiple-testing question PBO answers is "if I pick the best of the
strategies I TRIED, does it hold up out of sample?" So the trials must be
*structurally different strategies* — different asset-class mandates and different
momentum horizons — not knob perturbations of one book (vol_window / band /
rebalance), whose returns cluster so tightly that PBO only ever measures
knob-tuning noise.

This runs the allocator backtest (`allocator.backtest.engine.run_backtest`)
over the cross of:
  - sleeve mandate (`sleeve_caps`): how much each asset-class sleeve may hold —
    balanced / equity-tilt / defensive / all-weather / real-assets / credit-tilt,
  - trend horizon (`lookbacks`): fast / medium / slow time-series momentum,
and writes a wide CSV of per-period (monthly) net returns: one column per strategy
plus the registered-primary `chosen` column (balanced mandate, medium horizon —
matching `allocator.scripts.run_backtest`).

DEV TOOL, not part of the `crucible` package: it imports the allocator. The committed
artifact (`tests/fixtures/allocator_export.csv`) is generic CSV with no allocator
dependency, so the test suite stays hermetic.

    ALLOCATOR_SRC=/home/regan/apps/Schwab/allocator \
        python examples/gen_allocator_trials.py
"""
from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import pandas as pd

ALLOC = os.environ.get("ALLOCATOR_SRC", "/home/regan/apps/Schwab/allocator")
sys.path.insert(0, ALLOC)

from allocator.backtest.engine import BacktestConfig, run_backtest  # noqa: E402
from allocator.config import settings  # noqa: E402
from allocator.data.store import load_panel  # noqa: E402
from allocator.universe import Sleeve, all_tickers, by_ticker  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "allocator_export.csv"

# ── Sleeve mandates: max weight per asset-class sleeve (cash absorbs the residual,
# so CASH stays 1.0). Each is a genuinely different strategic book. "balanced" is the
# registered primary (allocator.universe.SLEEVE_CAPS). ────────────────────────────
_S = Sleeve
SLEEVE_SCHEMES: dict[str, dict] = {
    "balanced":    {_S.US_EQUITY: .35, _S.INTL_EQUITY: .25, _S.RATES: .45, _S.INFLATION: .15,
                    _S.CREDIT: .20, _S.COMMODITY: .20, _S.REAL_ESTATE: .10, _S.CASH: 1.0},
    "equity_tilt": {_S.US_EQUITY: .55, _S.INTL_EQUITY: .40, _S.RATES: .20, _S.INFLATION: .10,
                    _S.CREDIT: .15, _S.COMMODITY: .15, _S.REAL_ESTATE: .15, _S.CASH: 1.0},
    "defensive":   {_S.US_EQUITY: .15, _S.INTL_EQUITY: .10, _S.RATES: .65, _S.INFLATION: .20,
                    _S.CREDIT: .10, _S.COMMODITY: .10, _S.REAL_ESTATE: .05, _S.CASH: 1.0},
    "all_weather": {_S.US_EQUITY: .30, _S.INTL_EQUITY: .20, _S.RATES: .55, _S.INFLATION: .25,
                    _S.CREDIT: .15, _S.COMMODITY: .25, _S.REAL_ESTATE: .10, _S.CASH: 1.0},
    "real_assets": {_S.US_EQUITY: .20, _S.INTL_EQUITY: .15, _S.RATES: .30, _S.INFLATION: .30,
                    _S.CREDIT: .15, _S.COMMODITY: .35, _S.REAL_ESTATE: .20, _S.CASH: 1.0},
    "credit_tilt": {_S.US_EQUITY: .25, _S.INTL_EQUITY: .20, _S.RATES: .35, _S.INFLATION: .15,
                    _S.CREDIT: .40, _S.COMMODITY: .15, _S.REAL_ESTATE: .10, _S.CASH: 1.0},
}

# ── Trend horizons: time-series-momentum lookbacks (trading days). Different alpha
# signals, not the same one re-tuned. "medium" is the primary (DEFAULT_LOOKBACKS). ──
TREND_HORIZONS: dict[str, tuple[int, ...]] = {
    "fast":   (21, 63),
    "medium": (21, 63, 126, 252),
    "slow":   (126, 252),
}

PRIMARY = ("balanced", "medium")   # the chosen / registered strategy


def _monthly(net: pd.Series) -> pd.Series:
    """Compound daily net returns to month-end per-period returns (smaller fixture,
    and aligns with the macro regime classifier's monthly cadence for Task 2)."""
    return (1.0 + net).resample("ME").prod() - 1.0


def main() -> int:
    prices = load_panel(all_tickers(), settings.data_dir)
    universe = by_ticker()

    columns: dict[str, pd.Series] = {}
    primary_key: str | None = None
    for i, (scheme, horizon) in enumerate(itertools.product(SLEEVE_SCHEMES, TREND_HORIZONS)):
        cfg = BacktestConfig(start=settings.backtest_start, lookbacks=TREND_HORIZONS[horizon])
        res = run_backtest(prices, universe, SLEEVE_SCHEMES[scheme], cfg)
        key = f"trial_{i:02d}"
        columns[key] = _monthly(res.net_returns)
        if (scheme, horizon) == PRIMARY:
            primary_key = key
        s = columns[key]
        sharpe = s.mean() / s.std() if s.std() else float("nan")
        print(f"  {key}: {scheme:<11} {horizon:<6} -> {len(s):>3} months, "
              f"per-period sharpe {sharpe:+.3f}")

    if primary_key is None:
        raise SystemExit("primary strategy not present in the variant grid")

    df = pd.DataFrame(columns).dropna()          # align to the common monthly window
    df.insert(0, "chosen", df[primary_key])      # chosen = registered primary
    df.index.name = "date"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT)
    print(f"\nwrote {OUT}")
    print(f"  {df.shape[0]} months x {len(columns)} strategies  "
          f"({df.index.min().date()} -> {df.index.max().date()}, chosen={primary_key} "
          f"= {PRIMARY[0]}/{PRIMARY[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
