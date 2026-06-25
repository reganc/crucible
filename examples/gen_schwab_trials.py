"""Generate a real Schwab-allocator trial export for CRUCIBLE's ingest adapter.

Runs the Schwab allocator backtest (`allocator.backtest.engine.run_backtest`)
across a grid of `BacktestConfig` variants over the cached price panel, and writes
a wide CSV of per-period (monthly) net returns: one column per config variant
tried (the multiple-testing evidence) plus the registered-primary `chosen` column.

This is the engine-specific *export* the KICKOFF calls for — the Schwab equivalent
of a DELPHI backtest dump. Its schema is consumed only by
`crucible.ingest.load_schwab`; nothing else in CRUCIBLE imports Schwab.

This script is a DEV TOOL, not part of the `crucible` package: it imports the
Schwab allocator. The committed artifact (`tests/fixtures/schwab_export.csv`) is
generic CSV and carries no Schwab dependency, so the test suite stays hermetic.

    SCHWAB_ALLOCATOR=/home/regan/apps/Schwab/allocator \
        python examples/gen_schwab_trials.py
"""
from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import pandas as pd

ALLOC = os.environ.get("SCHWAB_ALLOCATOR", "/home/regan/apps/Schwab/allocator")
sys.path.insert(0, ALLOC)

from allocator.backtest.engine import BacktestConfig, run_backtest  # noqa: E402
from allocator.config import settings  # noqa: E402
from allocator.data.store import load_panel  # noqa: E402
from allocator.universe import SLEEVE_CAPS, all_tickers, by_ticker  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "schwab_export.csv"

# Registered primary = the chosen strategy (matches allocator.scripts.run_backtest
# defaults). One of the swept variants below equals this; it becomes `chosen`.
PRIMARY = {"vol_window": 63, "no_trade_band": 0.005, "rebalance": "W-FRI"}

# A researcher's sweep — genuine allocator config variants. The product is the
# honest multiple-testing count CRUCIBLE deflates against.
VOL_WINDOWS = (42, 63, 84)
BANDS = (0.0025, 0.005, 0.01)
REBALANCES = ("W-FRI", "W-MON", "ME")


def _variants() -> list[dict]:
    return [
        {"vol_window": vw, "no_trade_band": band, "rebalance": reb}
        for vw, band, reb in itertools.product(VOL_WINDOWS, BANDS, REBALANCES)
    ]


def _monthly(net: pd.Series) -> pd.Series:
    """Compound daily net returns to month-end per-period returns (smaller fixture,
    and aligns with the macro regime classifier's monthly cadence for Task 2)."""
    return (1.0 + net).resample("ME").prod() - 1.0


def main() -> int:
    prices = load_panel(all_tickers(), settings.data_dir)
    universe, caps = by_ticker(), SLEEVE_CAPS

    columns: dict[str, pd.Series] = {}
    primary_key: str | None = None
    for i, v in enumerate(_variants()):
        cfg = BacktestConfig(start=settings.backtest_start, **v)
        res = run_backtest(prices, universe, caps, cfg)
        key = f"trial_{i:02d}"
        columns[key] = _monthly(res.net_returns)
        if v == PRIMARY:
            primary_key = key
        s = columns[key]
        sharpe = s.mean() / s.std() if s.std() else float("nan")
        print(f"  {key}: vw={v['vol_window']:>2} band={v['no_trade_band']:<6} "
              f"reb={v['rebalance']:<5} -> {len(s):>3} months, per-period sharpe {sharpe:+.3f}")

    if primary_key is None:
        raise SystemExit("primary config not present in the variant grid")

    df = pd.DataFrame(columns).dropna()          # align to the common monthly window
    df.insert(0, "chosen", df[primary_key])      # chosen = registered primary
    df.index.name = "date"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT)
    print(f"\nwrote {OUT}")
    print(f"  {df.shape[0]} months x {len(columns)} trials  "
          f"({df.index.min().date()} -> {df.index.max().date()}, chosen={primary_key})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
