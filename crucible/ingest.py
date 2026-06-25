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


def load_schwab(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Adapter for a Schwab allocator backtest export -> CRUCIBLE's generic shapes.

    The export (produced by examples/gen_schwab_trials.py, which runs the Schwab
    allocator's walk-forward backtest across a grid of BacktestConfig variants) is a
    wide CSV of per-period returns:
      - a leading ``date`` column (per-period; the committed fixture is monthly),
      - a ``chosen`` column: the registered-primary strategy's per-period returns,
      - one ``trial_<i>`` column per config variant evaluated (the multiple-testing set).

    Returns ``(trials_matrix, chosen_returns)``:
      - trials_matrix : (T x N) float array, one column per variant -> drives PBO and
        the trial-Sharpe variance for DSR deflation.
      - chosen_returns : (T,) float array -> the series PSR/DSR/minTRL score.

    Schwab's schema is known *here* and converted to generic numpy. It does not leak
    past this function — the verdict only ever sees a matrix and a 1-D series.
    """
    df = pd.read_csv(path)
    if df.columns[0].lower() in ("date", "time", "timestamp", "index", "unnamed: 0"):
        df = df.iloc[:, 1:]
    trial_cols = [c for c in df.columns if c.startswith("trial_")]
    if len(trial_cols) < 2:
        raise ValueError(
            f"Schwab export must have >= 2 'trial_*' columns (the variants tried); "
            f"found {len(trial_cols)}"
        )
    if "chosen" not in df.columns:
        raise ValueError("Schwab export missing required 'chosen' column")
    trials = df[trial_cols].to_numpy(dtype=float)
    chosen = df["chosen"].to_numpy(dtype=float)
    return trials, chosen
