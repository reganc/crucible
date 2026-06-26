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
- **Task 1 — Schwab ingestion adapter** (`823cb49`) — `ingest.load_schwab` → (T×N matrix,
  chosen series); real fixture `tests/fixtures/schwab_export.csv` (27 allocator variants,
  257 months, 2005–2026) via `examples/gen_schwab_trials.py`; `tests/test_ingest_schwab.py`.
  Verdict is RED via **PBO 0.76 while DSR 1.0** — config-selection is overfit, base edge
  survives deflation.
- **Task 2 — Regime-conditional deflation** (`b1aa769`) — `regime.PrecomputedRegime` +
  `verdict.RegimeDeflation` (DSR_full vs DSR_ex_dominant_regime, regime-captive note at
  drop ≥ 0.5); `ingest.schwab_regime_classifier` wraps the macro six-regime output. Real
  fixture `tests/fixtures/schwab_regimes.csv` (live FRED, 263 months, 85% NBER recall);
  `tests/test_regime.py` + `tests/test_ingest_schwab_regime.py`. On the real allocator the edge
  is **not** regime-captive: dominant regime DISINFLATION, DSR 1.000 → 0.990.

Suite: **17 passing.** noise→RED / real→GREEN invariant intact.

## Queued — open questions raised at task checkpoints (need a call before building)

- **Define "the variants you tried" for Schwab.** The 27 trials are knob perturbations
  (vol_window × no-trade band × rebalance) → tightly clustered Sharpes → PBO reads
  *config selection* as overfit. For PBO to speak to competing **strategies**, the sweep should
  include structurally different variants (signal families, sleeve schemes), not just knobs.
- **Daily vs monthly deflation.** Fixtures are monthly (compounded) for size + macro-regime
  alignment. Switch to daily if you want the allocator's native cadence.
- **Make the regime test bite on real data.** The allocator is broad multi-asset (regime-robust
  by design), so Task 2 shows ~no collapse. Point it at a regime-dependent sleeve (e.g. a
  momentum book) to exercise a genuine DSR collapse on real data.

## Parked / later

- Optional capacity / transaction-cost realism layer before the verdict (from CLAUDE.md "Next").
- `trading-api` market regime brain (BULL…BEAR) as an alternative classifier if a market-state
  (not macro-economic) lens is wanted — needs live DB/Redis/Yahoo, so not offline-reproducible.
- Hygiene: the FRED key in `~/apps/Schwab/research-api/.env` was exposed in a prior session's
  logs (free key; rotate if you care) and its value carries a trailing inline comment — strip
  everything after `#` when reusing it.
