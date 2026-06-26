"""
Ingestion adapters — engine- and data-agnostic.

CRUCIBLE consumes the *output* of whatever backtester you already use (DELPHI, LEAN,
Nautilus, VectorBT, a CSV). The two shapes it needs:

  1. A trial matrix: (T observations x N trials) of per-period returns — one column per
     strategy variant you tried during research. This drives PBO and the trial-Sharpe
     variance for DSR.
  2. A single strategy's return series — for PSR/DSR/minTRL on the chosen strategy.

If all you have is the chosen strategy's returns plus a count of how many variants you
tried, that's enough for DSR (pass n_trials explicitly); PBO needs the full matrix.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crucible.regime import PrecomputedRegime


def load_trial_matrix(path: str) -> np.ndarray:
    """Load a (T x N) matrix of per-period returns from CSV (rows=time, cols=trials)."""
    df = pd.read_csv(path)
    # drop a leading date/index column if present
    if df.columns[0].lower() in ("date", "time", "timestamp", "index", "unnamed: 0"):
        df = df.iloc[:, 1:]
    return df.to_numpy(dtype=float)


def trial_sharpe_variance(returns_matrix: np.ndarray) -> float:
    """Variance of per-period Sharpe ratios across trials — the DSR deflation input."""
    from crucible.metrics import sharpe
    M = np.asarray(returns_matrix, dtype=float)
    srs = np.array([sharpe(M[:, j]) for j in range(M.shape[1])])
    return float(np.var(srs, ddof=1)) if srs.size > 1 else 0.0


def returns_from_series(path: str, column: str | None = None) -> np.ndarray:
    """Load a single strategy's per-period returns from a CSV column."""
    df = pd.read_csv(path)
    if column is not None:
        return df[column].to_numpy(dtype=float)
    # else take the last numeric column
    numeric = df.select_dtypes("number")
    return numeric.iloc[:, -1].to_numpy(dtype=float)


def load_allocator(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Adapter for an allocator backtest export -> CRUCIBLE's generic shapes.

    The export (produced by examples/gen_allocator_trials.py, which runs the
    allocator's walk-forward backtest across a grid of BacktestConfig variants) is a
    wide CSV of per-period returns:
      - a leading ``date`` column (per-period; the committed fixture is monthly),
      - a ``chosen`` column: the registered-primary strategy's per-period returns,
      - one ``trial_<i>`` column per config variant evaluated (the multiple-testing set).

    Returns ``(trials_matrix, chosen_returns)``:
      - trials_matrix : (T x N) float array, one column per variant -> drives PBO and
        the trial-Sharpe variance for DSR deflation.
      - chosen_returns : (T,) float array -> the series PSR/DSR/minTRL score.

    The allocator's schema is known *here* and converted to generic numpy. It does not leak
    past this function — the verdict only ever sees a matrix and a 1-D series.
    """
    df = pd.read_csv(path)
    if df.columns[0].lower() in ("date", "time", "timestamp", "index", "unnamed: 0"):
        df = df.iloc[:, 1:]
    trial_cols = [c for c in df.columns if c.startswith("trial_")]
    if len(trial_cols) < 2:
        raise ValueError(
            f"allocator export must have >= 2 'trial_*' columns (the variants tried); "
            f"found {len(trial_cols)}"
        )
    if "chosen" not in df.columns:
        raise ValueError("allocator export missing required 'chosen' column")
    trials = df[trial_cols].to_numpy(dtype=float)
    chosen = df["chosen"].to_numpy(dtype=float)
    return trials, chosen


# allocator research-api macro six-regime labels -> stable integer ids. The order traces
# the economic cycle; the ids are arbitrary but fixed. Anything else (NO_DATA, warmup,
# an unknown label) maps to -1 and the verdict treats it as its own regime.
MACRO_REGIMES: dict[str, int] = {
    "GOLDILOCKS": 0,
    "REFLATION": 1,
    "STAGFLATION": 2,
    "DISINFLATION": 3,
    "LATE_CYCLE": 4,
    "RECESSION": 5,
}


def load_allocator_regimes(path: str) -> pd.Series:
    """Load an allocator macro-regime export into a month-indexed integer regime series.

    The export is what `Schwab/research-api/tests/backtest_regime.py --csv` writes:
    a per-month CSV with at least `date` and `regime` columns, `regime` being a macro
    label (GOLDILOCKS … RECESSION). The allocator's regime enum is known here and mapped to ints; it
    does not leak past the ingest seam.
    """
    df = pd.read_csv(path)
    if "regime" not in df.columns or "date" not in df.columns:
        raise ValueError("allocator regime export needs 'date' and 'regime' columns")
    ids = df["regime"].astype(str).str.upper().map(lambda s: MACRO_REGIMES.get(s, -1))
    series = pd.Series(
        ids.to_numpy(dtype=int),
        index=pd.PeriodIndex(pd.to_datetime(df["date"]), freq="M"),
        name="regime",
    )
    return series[~series.index.duplicated(keep="last")].sort_index()


def allocator_regime_classifier(returns_export_path: str, regime_csv_path: str) -> PrecomputedRegime:
    """Build a date-aligned RegimeClassifier for an allocator returns export.

    Joins the macro-regime series onto the per-period (monthly) dates of the returns
    export — as-of by calendar month, forward-filling months with no fresh
    classification — and returns a generic `PrecomputedRegime`. This is where the
    macro-regime schema is converted to one integer label per observation and stops.
    """
    months = pd.PeriodIndex(
        pd.to_datetime(pd.read_csv(returns_export_path, usecols=[0]).iloc[:, 0]), freq="M"
    )
    regimes = load_allocator_regimes(regime_csv_path)
    aligned = regimes.reindex(months, method="ffill")
    if aligned.isna().any():               # export months preceding the regime series
        aligned = aligned.bfill()
    return PrecomputedRegime(aligned.to_numpy(dtype=int))
