# CRUCIBLE

**A severe test for trading edges.** Feed it the output of whatever backtester you
already use; it tells you — honestly — whether your edge is real or just the best of
N noisy tries. The job of this tool is sometimes to disappoint you.

It is engine- and data-agnostic on purpose: it consumes a matrix of trial returns or a
single strategy's return series, not a specific platform's internals. It sits *on top of*
DELPHI / LEAN / Nautilus / VectorBT, not in competition with them.

## What it computes

- **Deflated Sharpe Ratio (DSR)** — your Sharpe, corrected for how many variants you
  tried, plus sample length, skew, and kurtosis. The headline honesty number.
- **Probability of Backtest Overfitting (PBO)** via CSCV — how often your in-sample
  pick lands below median out-of-sample.
- **Probabilistic Sharpe (PSR)** and **minimum track record length** — is your sample
  even long enough to claim the edge?
- **Regime-conditional Sharpe** — a seam for the six-regime brain, to catch edges that
  live in one regime only.

## Quickstart

```bash
pip install -e .
python examples/make_demo_data.py
crucible verdict noise_trials.csv     # -> RED  (DSR ~0.47, PBO ~0.5)
crucible verdict real_trials.csv      # -> GREEN (DSR ~1.0, PBO ~0.0)
pytest -q
```

The demo is the point: the noise matrix shows a tempting PSR-vs-0 near 0.98 — and a
deflated Sharpe near 0.5 that calls it a coin flip.

## Library use

```python
from crucible import assess
v = assess(chosen_returns, n_trials=200, trials_matrix=M)  # M is (T x N)
print(v.band, v.headline, v.deflation.deflated_sharpe, v.pbo.pbo)
```

## Build-vs-import notes

- `crucible/psr.py`, `crucible/pbo.py` — built here (compact, from the Bailey /
  López de Prado papers), so the verdict engine owns them end to end.
- `crucible/cpcv.py` — thin seam over **skfolio**'s `CombinatorialPurgedCV`
  (`pip install crucible[cpcv]`); the package still runs without it.
- `crucible/regime.py` — seam for the six-regime classifier (stub ships single-regime).
- `crucible/verdict.py` — the orchestration: the actual product.
