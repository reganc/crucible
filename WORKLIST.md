# WORKLIST — CRUCIBLE

Tactical, moving-picture status: what's done, what's in flight, what's queued, what's
parked. CLAUDE.md holds stable conventions and the load-bearing decisions; this file is
the live picture. **Read it before starting new work; update it when work lands.**

## Done

- **Bootstrap** (`7f2772c`) — deploy v1 unzipped; baseline verified (noise→RED DSR 0.47 /
  PBO 0.50, real→GREEN DSR 1.0 / PBO 0.0; 8 tests). CLAUDE.md authored (operating posture +
  permissions + non-negotiables). Pushed to `github.com/reganc/crucible`.
- **Step 1 discovery checkpoint** — KICKOFF named "DELPHI", but DELPHI is a Polymarket engine
  with no regime classifier and no (T×N) matrix. **Pivoted to `~/apps/Schwab`** (confirmed):
  allocator backtest = the export; research-api macro **six-regime** classifier = the regime
  brain; regime labels **date-aligned** to returns. (Details in CLAUDE.md → Integration source.)
- **Task 1 — allocator ingestion adapter** (`823cb49`) — `ingest.load_allocator` → (T×N matrix,
  chosen series); real fixture `tests/fixtures/allocator_export.csv` via
  `examples/gen_allocator_trials.py`; `tests/test_ingest_allocator.py`. (Fixture later rebuilt — see
  the trial-set entry below.)
- **Task 2 — Regime-conditional deflation** (`b1aa769`) — `regime.PrecomputedRegime` +
  `verdict.RegimeDeflation` (DSR_full vs DSR_ex_dominant_regime, regime-captive note at
  drop ≥ 0.5); `ingest.allocator_regime_classifier` wraps the macro six-regime output. Real
  fixture `tests/fixtures/allocator_regimes.csv` (live FRED, 263 months, 85% NBER recall);
  `tests/test_regime.py` + `tests/test_ingest_allocator_regime.py`. On the real allocator the edge
  is **not** regime-captive: dominant regime DISINFLATION, DSR 1.000 → 0.990.

- **Trial set = structurally distinct strategies** — `examples/gen_allocator_trials.py` now sweeps
  6 sleeve mandates (balanced / equity-tilt / defensive / all-weather / real-assets / credit-tilt)
  × 3 trend horizons (fast / medium / slow) = **18 strategies**, 258 months. Chosen = the
  registered primary (balanced / medium), which is mid-pack (defensive beats it in-sample, so
  PBO isn't gamed by picking the winner).
  **Finding — the verdict is trial-set-dependent, and that is the real lesson:**
  - 27 knob perturbations → near-identical returns → **PBO 0.76 → RED** (you can't reliably pick
    the best *knob setting*; selecting among indistinguishable books is overfitting).
  - 18 distinct strategies → dispersed returns → **PBO 0.11, DSR 0.999 → GREEN** (selecting among
    genuinely different *strategies* holds up out of sample). Still not regime-captive
    (DSR 0.999 → 0.968 ex-DISINFLATION).
  PBO is only as meaningful as the trial set faithfully represents the search you actually ran.
  Honest read on the allocator: don't trust knob-tuning, but the chosen mandate is defensible.

- **Public-facing polish** (`801b2bf`, `4532443`, `748c7f8`) — README documents the allocator
  integration; the brokerage name is removed repo-wide (API / filenames / prose now use generic
  `allocator` / `load_allocator` / `allocator_regime_classifier` …). Only the real
  `~/apps/Schwab/...` paths needed to regenerate fixtures remain.

- **Regime-captive detector validated on real data** — added a contrasting real fixture
  (`tests/fixtures/cyclicals_export.csv`, raw cyclical ETF holdings) via
  `examples/gen_cyclicals_export.py`, plus `examples/verdict_regime_captive.py` and
  `tests/test_regime_captive_real.py`. **Finding:** no allocator-engine book is regime-captive —
  vol-targeting + the market regime overlay make every book broadly positive across all six
  macro regimes (DSR 0.999 → 0.968 ex-regime). The detector *does* fire on genuinely regime-
  dependent holdings: raw small-caps **IWM** DSR **0.867 → 0.274 (Δ0.59)**, captive note triggered;
  EEM / VGK similar. So Task 2 catches what it should and stays quiet on what it shouldn't.
  (The sample-size caveat was the follow-up below.)

- **Sample-size-controlled regime deflation** — the ex-regime DSR drop blended regime-dependence
  with shorter-sample effects. `RegimeDeflation` now also carries the n-independent per-period
  Sharpe (full vs ex-dominant) and a fixed-`n` bootstrap: the DSR over equal-sized RANDOM
  removals plus the percentile the real ex-regime DSR lands at (`regime_specific`). `regime_captive`
  now requires the collapse to be regime-specific (left tail), not merely large — a shorter sample
  can no longer masquerade as captivity. On real data: IWM per-period Sharpe **0.145 → 0.015**,
  ex-DSR at the **1st** percentile of random removals → genuinely captive; the allocator's
  0.999 → 0.968 sits at the **19th** percentile → sample-size, correctly NOT flagged.
  `tests/test_regime.py` gains a sample-size-artifact case + a determinism check.

- **Daily vs monthly deflation — resolved** — added a `CRUCIBLE_CADENCE` knob to
  `examples/gen_allocator_trials.py` (monthly default → the small committed fixture; `daily` →
  native, written to a separate file so the committed fixture is never clobbered) and
  `examples/compare_cadence.py`. **Finding:** the verdict is cadence-robust for this allocator —
  both GREEN, DSR 0.999, PBO 0.11 (monthly) / 0.08 (daily), minTRL agrees in time (~3.5 yr). The
  real difference is non-normality: daily skew **−0.51** / kurtosis **6.28** vs monthly +0.01 /
  3.87. Monthly compounding Gaussianises the returns (CLT) and hides the tail risk the Deflated
  Sharpe is built to penalise — so **daily is the honest cadence for a real assessment**; monthly
  is kept for small/fast hermetic tests (and here doesn't change the call).

- **Capacity / transaction-cost layer** — `crucible/capacity.py` (a pre-verdict seam; never
  touches the DSR/PBO math). Haircuts gross returns for linear cost + square-root market impact
  (`CostModel`, `net_returns`, `net_sharpe`) and solves the **capacity** — the AUM where net
  Sharpe hits zero (`capacity_aum`, by bisection). Costs only ever subtract (no flattering).
  `tests/test_capacity.py` (8 cases: identity, monotonicity, sqrt-law, break-even, unbounded /
  zero edge cases) + `examples/capacity_curve.py`. On the real allocator edge: zero-cost
  GREEN / DSR 0.999 survives deflation, but at **$10B AUM** market impact takes net Sharpe to
  −0.02 and the Deflated Sharpe to **0.125 → RED** — a real edge that's untradeable at scale.

Suite: **29 passing.** noise→RED / real→GREEN invariant intact.

## Queued

_Nothing queued — next candidates are under Parked / later._

## Parked / later

- `trading-api` market regime brain (BULL…BEAR) as an alternative classifier if a market-state
  (not macro-economic) lens is wanted — needs live DB/Redis/Yahoo, so not offline-reproducible.
- Hygiene: the FRED key in `~/apps/Schwab/research-api/.env` was exposed in a prior session's
  logs (free key; rotate if you care) and its value carries a trailing inline comment — strip
  everything after `#` when reusing it.
