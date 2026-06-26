# CRUCIBLE

**A severe test for trading edges.** Feed it the output of whatever backtester you
already use; it tells you — honestly — whether your edge is real or just the best of
N noisy tries. The job of this tool is sometimes to disappoint you.

It is engine- and data-agnostic on purpose: it consumes a matrix of trial returns or a
single strategy's return series, not a specific platform's internals. It sits *on top of*
your backtester (LEAN / Nautilus / VectorBT / a CSV), not in competition with it. A concrete
adapter ships for a **systematic ETF allocator** — see [Allocator integration](#allocator-integration).

## What it computes

- **Deflated Sharpe Ratio (DSR)** — your Sharpe, corrected for how many variants you
  tried, plus sample length, skew, and kurtosis. The headline honesty number.
- **Probability of Backtest Overfitting (PBO)** via CSCV — how often your in-sample
  pick lands below median out-of-sample.
- **Probabilistic Sharpe (PSR)** and **minimum track record length** — is your sample
  even long enough to claim the edge?
- **Regime-conditional Deflated Sharpe** — recomputes the DSR with the dominant regime's
  observations removed and surfaces the drop, answering "does the edge survive when you
  remove the regime it was born in?" Catches edges that live in one regime only.

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

## Allocator integration

A concrete adapter wires CRUCIBLE to a systematic ETF allocator. The allocator's schema stays
inside `crucible/ingest.py`; the verdict only ever sees a generic trial matrix and a 1-D
return series.

```python
from crucible import assess
from crucible.ingest import load_allocator, allocator_regime_classifier

trials, chosen = load_allocator("tests/fixtures/allocator_export.csv")    # (T x N), (T,)
clf = allocator_regime_classifier(                                        # date-aligned
    "tests/fixtures/allocator_export.csv", "tests/fixtures/allocator_regimes.csv")
v = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials, regime=clf)
print(v.band, v.regime_deflation.dsr_full, v.regime_deflation.dsr_ex_dominant)
```

- **`load_allocator`** reads a backtest export (one column per strategy variant tried, plus the
  registered-primary `chosen` column) into the matrix + chosen series the verdict consumes.
- **`allocator_regime_classifier`** wraps the allocator's macro **six-regime** classifier
  (GOLDILOCKS / REFLATION / STAGFLATION / DISINFLATION / LATE_CYCLE / RECESSION), date-aligning
  one integer regime per observation so `assess(regime=…)` can report the regime-conditional DSR.
- Runnable demos on committed real fixtures: `examples/verdict_allocator.py`,
  `examples/verdict_allocator_regime.py`. Regenerate fixtures with `examples/gen_allocator_trials.py`.

**The trials must be the search you actually ran.** PBO/CSCV only means something when the
trial columns are the *competing strategies* you chose between. The shipped sweep is 18
structurally distinct strategies (6 sleeve mandates × 3 trend horizons) → PBO 0.11, DSR 0.999,
**GREEN**. An earlier sweep of 27 near-identical *knob* perturbations of one book → PBO 0.76,
**RED**: same allocator, opposite verdict, because picking the best of 27 indistinguishable
configs is overfitting while picking among real strategies is not. The verdict is only as
honest as the trial set.

## Build-vs-import notes

- `crucible/psr.py`, `crucible/pbo.py` — built here (compact, from the Bailey /
  López de Prado papers), so the verdict engine owns them end to end.
- `crucible/cpcv.py` — thin seam over **skfolio**'s `CombinatorialPurgedCV`
  (`pip install crucible[cpcv]`); the package still runs without it.
- `crucible/regime.py` — regime seam: `SingleRegime` (no-dependency fallback) and
  `PrecomputedRegime` (carries date-aligned labels from the allocator's macro six-regime classifier).
- `crucible/verdict.py` — the orchestration: the actual product.
