"""Daily vs monthly deflation — does the cadence change the verdict?

Runs the same 18 allocator strategies at daily (native) and monthly (compounded)
cadence and prints the deflation side by side. Finding: the band is cadence-robust
here, but monthly compounding masks the daily skew/kurtosis the Deflated Sharpe is
meant to penalise (daily skew ~-0.5, kurtosis ~6 -> monthly ~0 / ~4). Prefer daily
for a real assessment; monthly can flatter a more crash-prone strategy.

    ALLOCATOR_SRC=/home/regan/apps/Schwab/allocator python examples/compare_cadence.py
"""
from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))           # reuse the sweep definitions from the generator
from gen_allocator_trials import PRIMARY, SLEEVE_SCHEMES, TREND_HORIZONS  # noqa: E402

ALLOC = os.environ.get("ALLOCATOR_SRC", "/home/regan/apps/Schwab/allocator")
sys.path.insert(0, ALLOC)
from allocator.backtest.engine import BacktestConfig, run_backtest  # noqa: E402
from allocator.config import settings  # noqa: E402
from allocator.data.store import load_panel  # noqa: E402
from allocator.universe import all_tickers, by_ticker  # noqa: E402

sys.path.insert(0, str(HERE.parent))
from crucible.ingest import load_allocator_regimes  # noqa: E402
from crucible.metrics import moments  # noqa: E402
from crucible.regime import PrecomputedRegime  # noqa: E402
from crucible.verdict import assess  # noqa: E402

REGIMES = HERE.parent / "tests" / "fixtures" / "allocator_regimes.csv"


def _regime_clf(index, regimes) -> PrecomputedRegime:
    months = pd.PeriodIndex(index, freq="M")
    aligned = regimes.reindex(months, method="ffill")
    if aligned.isna().any():
        aligned = aligned.bfill()
    return PrecomputedRegime(aligned.to_numpy(dtype=int))


def main() -> int:
    prices = load_panel(all_tickers(), settings.data_dir)
    universe = by_ticker()
    daily: dict[str, pd.Series] = {}
    primary = None
    for i, (scheme, horizon) in enumerate(itertools.product(SLEEVE_SCHEMES, TREND_HORIZONS)):
        res = run_backtest(prices, universe, SLEEVE_SCHEMES[scheme],
                           BacktestConfig(start=settings.backtest_start, lookbacks=TREND_HORIZONS[horizon]))
        key = f"trial_{i:02d}"
        daily[key] = res.net_returns
        if (scheme, horizon) == PRIMARY:
            primary = key
    D = pd.DataFrame(daily).dropna()
    M = (1.0 + D).resample("ME").prod() - 1.0
    regimes = load_allocator_regimes(str(REGIMES))

    print(f"\n{'cadence':<9}{'n':>6}{'sharpe':>9}{'skew':>8}{'kurt':>7}"
          f"{'DSR':>7}{'PBO':>7}{'band':>8}{'regime ΔDSR':>13}")
    for label, df in (("monthly", M), ("daily", D)):
        mat, chosen = df.values, df[primary].values
        v = assess(chosen, n_trials=mat.shape[1], trials_matrix=mat, regime=_regime_clf(df.index, regimes))
        mo, d, rd = moments(chosen), v.deflation, v.regime_deflation
        print(f"{label:<9}{len(df):>6}{mo['sharpe']:>9.4f}{mo['skew']:>8.3f}{mo['kurtosis']:>7.2f}"
              f"{d.deflated_sharpe:>7.3f}{v.pbo.pbo:>7.3f}{v.band.upper():>8}"
              f"{rd.dsr_full - rd.dsr_ex_dominant:>+13.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
