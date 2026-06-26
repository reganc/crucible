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
  chosen series); real fixture `tests/fixtures/schwab_export.csv` via
  `examples/gen_schwab_trials.py`; `tests/test_ingest_schwab.py`. (Fixture later rebuilt — see
  the trial-set entry below.)
- **Task 2 — Regime-conditional deflation** (`b1aa769`) — `regime.PrecomputedRegime` +
  `verdict.RegimeDeflation` (DSR_full vs DSR_ex_dominant_regime, regime-captive note at
  drop ≥ 0.5); `ingest.schwab_regime_classifier` wraps the macro six-regime output. Real
  fixture `tests/fixtures/schwab_regimes.csv` (live FRED, 263 months, 85% NBER recall);
  `tests/test_regime.py` + `tests/test_ingest_schwab_regime.py`. On the real allocator the edge
  is **not** regime-captive: dominant regime DISINFLATION, DSR 1.000 → 0.990.

- **Trial set = structurally distinct strategies** — `examples/gen_schwab_trials.py` now sweeps
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

Suite: **17 passing.** noise→RED / real→GREEN invariant intact.

## Queued — open questions raised at task checkpoints (need a call before building)

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
