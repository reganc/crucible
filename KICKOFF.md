# KICKOFF — CRUCIBLE handoff to Claude Code

You're picking up CRUCIBLE, a personal quant honesty-layer. Its job is to tell me—
honestly—whether a trading edge is real or just the best of N noisy tries. The tool's
job is sometimes to disappoint me. Never optimize for a satisfying result.

> Run this handoff from the machine where DELPHI actually lives (i.e. comet, where
> `~/apps/delphi` is on disk and readable). If that path doesn't resolve, STOP and tell
> me—do not invent a schema.

---

## Step 0 — Orient (do not skip)

1. Read `README.md` and `CLAUDE.md`.
2. Read `crucible/verdict.py` (the orchestration), `crucible/psr.py` and `crucible/pbo.py`
   (the verified stats), and the two seams: `crucible/regime.py` and `crucible/ingest.py`.
3. Run the baseline before changing anything:
   ```
   pip install -e '.[cpcv,dev]'
   python examples/make_demo_data.py
   crucible verdict noise_trials.csv   # must print RED  (DSR ~0.47, PBO ~0.5)
   crucible verdict real_trials.csv    # must print GREEN (DSR ~1.0,  PBO ~0.0)
   pytest -q                            # 8 tests, must be green
   ```
   If any of this doesn't hold, stop and tell me—don't proceed.

## Step 1 — Discover, then CHECKPOINT (do not build yet)

Explore `~/apps/delphi` and identify:

- **(a) The backtest export** that contains per-variant trial returns (a (T × N) matrix,
  one column per variant tried) *and* the chosen strategy's per-period return series.
- **(b) The regime classifier** module and the exact function/class that returns a
  regime label per observation.

Then **report back and WAIT for my confirmation before writing any adapter code**:
- the file paths you found,
- the relevant schema (columns/dtypes for the export) and the signature (function/class)
  for the classifier,
- any ambiguity. If multiple candidates exist for either, **list them and ask—do not pick
  one silently.** DELPHI likely has more than one CSV-ish output and more than one thing
  that looks regime-related; guessing wrong here costs commits to unwind.

## NON-NEGOTIABLES (override any instinct to "improve")

- **The core is engine- and data-agnostic.** `crucible/verdict.py`, `psr.py`, and `pbo.py`
  must NEVER import DELPHI or any specific backtester. Adapters live in `ingest.py` and
  convert external formats into the generic shapes the verdict already consumes (a (T × N)
  trial matrix and a 1-D return series). If supporting DELPHI seems to require editing
  `verdict.py`, the adapter boundary is wrong—fix the boundary, not the core.
- **The math stays correct and tested.** Do NOT alter the DSR/PSR/PBO formulas unless
  you've found a verified bug against Bailey & López de Prado (2012, 2014, 2015) AND you
  add a test proving the fix on a known case. They're currently validated: pure noise →
  DSR ~0.47 / PBO ~0.5, genuine edge → DSR ~1.0 / PBO ~0.0. Keep that property.
- **No flattering defaults, ever.** Nothing that hides multiple-testing, regime dependence,
  or overfitting. If a change makes a result look better without being more true, don't.
- **Verdicts are tooling for my own reasoning, not advice.** Keep all framing on that side.
- **Keep `pytest -q` green after every change.** The noise→RED / real→GREEN demo must keep
  passing throughout.

## Task 1 — DELPHI ingestion adapter (do FIRST, after the Step 1 checkpoint)

- Add a function to `crucible/ingest.py`, e.g. `load_delphi(path)`, that returns BOTH:
  (a) the (T × N) per-period trial-returns matrix, and
  (b) the chosen strategy's per-period return series.
  Match the verdict's existing inputs exactly; do not invent new shapes.
- It's fine for this function to know DELPHI's schema. It is NOT fine for that schema to
  leak past `ingest.py`. Convert to numpy/generic and stop there.
- Add a test in `tests/` that loads a real DELPHI fixture and runs `assess()` end to end,
  asserting the verdict object is well-formed (valid band, DSR in [0,1], PBO present when
  N ≥ 2).
- **Done when:** `crucible verdict` (or a short script) runs on the real DELPHI export and
  prints a verdict, with a passing test against a committed fixture.

## Task 2 — Regime-conditional verdict (do SECOND; higher-leverage)

- Implement a `RegimeClassifier` (the Protocol in `crucible/regime.py`) wrapping the
  DELPHI six-regime brain, so `.label(returns)` returns an integer regime per observation.
  Inject it; keep `SingleRegime` as the no-dependency fallback so the package still runs
  standalone.
- Add the real payoff: answer "does the edge survive when you remove the regime it was
  born in?" Identify the dominant regime (the one contributing most of the positive
  performance), recompute the Deflated Sharpe on the series with that regime's
  observations removed, and surface the delta (DSR_full vs DSR_ex_dominant_regime) in the
  `Verdict`. A large drop = the edge is regime-captive.
- Wire into `verdict.assess()` behind the `regime` parameter; when a real classifier is
  supplied and >1 regime is present, include the ex-regime DSR and add a note if the edge
  collapses without its home regime.
- Add tests: a synthetic series whose edge lives entirely in one regime must show a large
  DSR drop and trigger the note; a regime-robust edge must not.
- **Done when:** passing tests for both cases, and the CLI/verdict output shows the
  regime-conditional DSR when a real classifier is present.

## Working style

- Small commits, clear messages, one task at a time. Land Task 1 fully (green) before
  starting Task 2.
- Refactor behind the seams freely as long as tests stay green and the non-negotiables hold.
- After each task, give me a 3-line summary: what changed, what the test proves, and
  anything you had to decide that I should sanity-check.
