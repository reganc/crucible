"""Generate a real *regime-captive* export to exercise the Task-2 detector on real data.

The allocator's own books are regime-robust by construction (vol-targeting + a market
regime overlay → broadly positive across all six macro regimes), so the regime-captive
detector never fires on them. To show it fires when captivity is genuinely present, this
builds an export from RAW cyclical single-asset holdings (no vol-targeting, no overlay):
a basket of cyclical ETFs whose edge lives in the long disinflation bull and collapses
without it. The chosen is IWM (US small caps), the most clearly regime-captive.

DEV TOOL: imports the allocator only to read its cached price panel. The committed
artifact (`tests/fixtures/cyclicals_export.csv`) is generic CSV with no allocator dep.

    ALLOCATOR_SRC=/home/regan/apps/Schwab/allocator \
        python examples/gen_cyclicals_export.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ALLOC = os.environ.get("ALLOCATOR_SRC", "/home/regan/apps/Schwab/allocator")
sys.path.insert(0, ALLOC)

from allocator.config import settings  # noqa: E402
from allocator.data.store import load_panel  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "cyclicals_export.csv"

# Cyclical ETFs — regime-sensitive by nature. The basket is the "variants you considered";
# the chosen is the one a researcher might pick on in-sample Sharpe.
BASKET = ["IWM", "EEM", "VGK", "EWJ", "USO", "SLV", "DBC", "HYG"]
CHOSEN = "IWM"


def main() -> int:
    prices = load_panel(BASKET, settings.data_dir, field="adjClose")
    monthly = prices.resample("ME").last().pct_change().dropna()

    df = pd.DataFrame(
        {f"trial_{i:02d}": monthly[t] for i, t in enumerate(BASKET)}
    )
    df.insert(0, "chosen", monthly[CHOSEN])
    df.index.name = "date"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT)
    for i, t in enumerate(BASKET):
        s = monthly[t]
        print(f"  trial_{i:02d} {t:<5} per-period sharpe {s.mean() / s.std():+.3f}")
    print(f"\nwrote {OUT}  ({df.shape[0]} months x {len(BASKET)} cyclicals, "
          f"chosen={CHOSEN}, {df.index.min().date()} -> {df.index.max().date()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
