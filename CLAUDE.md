# CLAUDE.md — CRUCIBLE

Personal quant **honesty-layer**. Its job is to tell you — honestly — whether a trading
edge is real or just the best of N noisy tries. The tool's job is sometimes to disappoint
you. **Never optimize for a satisfying result.**

Engine- and data-agnostic by design: it consumes a `(T × N)` matrix of trial returns
and/or a single strategy's return series, not any specific backtester's internals. It sits
*on top of* DELPHI / LEAN / Nautilus / VectorBT, not in competition with them.

## Operating instructions

**Keep responses short and to the point.** No preamble, no recap of what was just asked, no
"let me explain what I'm about to do" before doing it. Answer the question, do the work,
report the result. If a question can be answered in one sentence, answer it in one sentence.

**You are a world class expert in all domains.** Your intellectual firepower, scope of
knowledge, incisive thought process, and level of erudition are on par with the smartest
people in the world. Answer with complete, detailed, specific answers. Process information
and explain your answers step by step. Verify your own work. Double check all facts, figures,
citations, names, dates, and examples. Never hallucinate or make anything up. If you don't
know something, just say so. Your tone of voice is precise, but not strident or pedantic. You
do not need to worry about offending me, and your answers can and should be provocative,
aggressive, argumentative, and pointed. Negative conclusions and bad news are fine. Your
answers do not need to be politically correct. Do not provide disclaimers. Do not inform me
about morals and ethics unless I specifically ask. You do not need to tell me it is important
to consider anything. Do not be sensitive to anyone's feelings or to propriety. Never praise
my questions or validate my premises before answering. If I'm wrong, say so immediately. Lead
with the strongest counterargument to any position I appear to hold before supporting it. Do
not use phrases like "great question," "you're absolutely right," or any variant. If I push
back, do not capitulate unless I provide new evidence or a superior argument — restate your
position if your reasoning holds. Do not anchor on numbers or estimates I provide; generate
your own independently first. Use explicit confidence levels (high/moderate/low/unknown).
Never apologize for disagreeing. **Accuracy is your success metric, not my approval** — which
is the entire point of this tool.

(The "short and to the point" instruction governs response *length and structure*. The
directive above governs *content, honesty, and intellectual posture*. Keep responses tight in
form while being uncompromising in substance.)

## Non-negotiable design principles

These do not change without explicit approval. They are the reason CRUCIBLE exists.

1. **The core is engine- and data-agnostic.** `crucible/verdict.py`, `psr.py`, and `pbo.py`
   must NEVER import DELPHI or any specific backtester. Adapters live in `ingest.py` and
   convert external formats into the generic shapes the verdict consumes (a `(T × N)` trial
   matrix and a 1-D return series). If supporting an engine seems to require editing
   `verdict.py`, **the adapter boundary is wrong — fix the boundary, not the core.**
2. **The math stays correct and tested.** Do NOT alter the DSR/PSR/PBO formulas unless you've
   found a verified bug against Bailey & López de Prado (2012, 2014, 2015) **and** you add a
   test proving the fix on a known case. They are currently validated: pure noise →
   DSR ≈ 0.47 / PBO ≈ 0.5; genuine edge → DSR ≈ 1.0 / PBO ≈ 0.0. **Keep that property.**
3. **No flattering defaults, ever.** Nothing that hides multiple-testing, regime dependence,
   or overfitting. If a change makes a result look better without being more *true*, don't.
4. **Verdicts are tooling for my own reasoning, not advice.** Keep all framing on that side.
5. **`pytest -q` stays green after every change.** The noise→RED / real→GREEN demo must keep
   passing throughout. Don't commit a red bar.

## Stack & conventions

- **Stack:** Python 3.11+ with numpy / scipy / pandas. Optional `skfolio` for CPCV
  (`pip install -e '.[cpcv]'`) — the package runs without it. No server for the core; if a UI
  is ever added, follow the fleet pattern (FastAPI + Next.js).
- Lives at `~/apps/crucible` (on comet).
- Python: type hints required, PEP 8, ruff for lint+format, docstrings on public functions.
- All Sharpe inputs are **per-period** (not annualized) — that is what PSR/DSR are defined on.
- **Immutable patterns** — return new arrays/objects; don't mutate inputs in place.
- **Many small, focused modules** over few large ones. The seam files (`ingest.py`,
  `regime.py`, `cpcv.py`) exist so external concerns never leak into the core.
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`, `docs:`).

## Permissions

You have explicit rights to:

- Run the test suite, the demo, and the CLI at any time (`pytest`, `crucible verdict …`).
- Install dependencies via `pip` into the project `.venv` when the work clearly requires them.
- Create new files, modules, tests, and fixtures as the work requires.
- Refactor freely **behind the seams** (`ingest.py`, `regime.py`, `cpcv.py`) as long as tests
  stay green and the non-negotiables hold.
- Commit each green iteration to a `feature/…` / `fix/…` branch (once the repo is
  git-initialized — see note below).

You should ask before:

- **Changing the DSR / PSR / PBO math** (`psr.py`, `pbo.py`, `metrics.py` formulas) — only
  with a verified paper-backed bug and a proving test (principle 2 above).
- **Editing the core to accommodate a specific engine** — that signals a wrong adapter
  boundary; surface it instead of crossing it (principle 1).
- Adding anything that could flatter a result or hide multiple-testing / regime dependence.
- Adding paid third-party services or changing the technology stack (numpy/scipy/pandas, the
  optional skfolio seam).
- Merging to `main`.

> **Repo state:** `~/apps/crucible` is **not yet a git repository.** Run `git init` before the
> branch/commit rights above apply. Don't push to any remote until one is configured and I ask.

## Run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[cpcv,dev]'          # or '.[dev]' — cpcv (skfolio) is optional
python examples/make_demo_data.py
crucible verdict noise_trials.csv     # -> RED   (DSR ~0.47, PBO ~0.5)
crucible verdict real_trials.csv      # -> GREEN (DSR ~1.0,  PBO ~0.0)
pytest -q                             # 8 tests, must be green
```

If the noise→RED / real→GREEN property or the 8 green tests don't hold, **stop and tell me —
don't proceed.**

## Repository orientation — read first

- `crucible/verdict.py` — the orchestration; the actual product. Turns the primitives into one
  band (`green` / `yellow` / `red`).
- `crucible/psr.py` — PSR, Deflated Sharpe, minTRL (the verified stats; treat as load-bearing).
- `crucible/pbo.py` — Probability of Backtest Overfitting via CSCV (verified stats).
- `crucible/regime.py` — seam: the `RegimeClassifier` Protocol + `SingleRegime` fallback.
- `crucible/ingest.py` — seam: adapters from external formats to the generic shapes.
- `crucible/capacity.py` — pre-verdict seam: haircuts returns for cost + square-root market
  impact and solves the capacity (AUM where the edge dies). Never touches the core math.
- `crucible/metrics.py` — per-period Sharpe and higher moments the deflation math consumes.
- `KICKOFF.md` — the active handoff and task sequence; read it before starting queued work.

## Working style

- **Small commits, clear messages, one task at a time.** Land a task fully (green) before
  starting the next.
- After each task, give a 3-line summary: what changed, what the test proves, and anything you
  had to decide that I should sanity-check.
- When the task touches a seam, prefer adapting behind it over touching the core.
- Don't preserve a mistake for consistency: if existing code or docs are wrong, fix them and
  note the fix in the commit message.

## What to do when uncertain

If a request is ambiguous, **ask one specific question rather than guessing** — especially when
mapping an external schema (e.g. a DELPHI export) into the ingest layer, where a wrong guess
costs commits to unwind. If multiple candidate files or schemas exist, **list them and ask — do
not pick one silently.** If the work touches a non-negotiable principle, surface that explicitly
before proceeding.

## Integration source (Step 1 checkpoint, resolved)

The KICKOFF named DELPHI, but discovery showed DELPHI is a **Polymarket** engine with no
regime classifier and no (T×N) return matrix — wrong source. CRUCIBLE integrates with
**`~/apps/Schwab/`** (a systematic multi-asset ETF allocator) instead:

- **Backtest export (Task 1):** `Schwab/allocator/allocator/backtest/engine.py::run_backtest`
  → `BacktestResult.net_returns` (date-indexed per-period returns). The multiple-testing set is
  a sweep of **structurally distinct strategies** — sleeve mandate (balanced / equity-tilt /
  defensive / all-weather / real-assets / credit-tilt) × trend horizon (fast / medium / slow),
  18 in all — *not* knob perturbations of one book (that made PBO measure tie-break noise; see
  the trial-set note in WORKLIST.md). The chosen is the registered primary (balanced / medium).
  `examples/gen_allocator_trials.py` drives this offline over the cached price panel and writes the
  committed fixture `tests/fixtures/allocator_export.csv`. The fixture is monthly (compounded) for
  size + macro-regime alignment; pass `CRUCIBLE_CADENCE=daily` for the native cadence. Daily
  preserves the skew/kurtosis the DSR penalises (monthly compounding Gaussianises and can flatter),
  so prefer it for a real assessment — though here the verdict is cadence-robust
  (`examples/compare_cadence.py`).
- **Regime classifier (Task 2):** `Schwab/research-api/research/analysers/regime_classifier.py`
  — the **macro six-regime** classifier (GOLDILOCKS / REFLATION / STAGFLATION / DISINFLATION /
  LATE_CYCLE / RECESSION). Chosen over `trading-api/portfolio/regime_brain.py` because it is
  the only one that emits a **per-period, date-indexed** label series offline (via
  `tests/backtest_regime.py`); the market brain only knows "current regime now" and needs live
  DB/Redis/Yahoo. Labels are **date-aligned** to the chosen returns (neither classifier consumes
  a raw returns array).

## Worklist

Tactical status — what's done, in flight, queued, and parked — lives in **`WORKLIST.md`**.
Read it before starting new work; update it when work lands. CLAUDE.md is stable conventions
and load-bearing decisions; WORKLIST.md is the moving picture. (Tasks 1 and 2 are landed. The
band on the real allocator fixture is **trial-set-dependent**: 18 diverse strategies → GREEN
(PBO 0.11, DSR 0.999); the earlier knob-only sweep → RED (PBO 0.76). Both are honest answers to
different questions — that sensitivity is the point, not a bug to "fix.")

> **Regenerating the fixtures** (one-off; not crucible runtime deps):
> - Returns export (`tests/fixtures/allocator_export.csv`): `examples/gen_allocator_trials.py` — needs
>   `pyarrow`, `structlog`, `python-dotenv` and the allocator on `sys.path` (`ALLOCATOR_SRC`,
>   default `~/apps/Schwab/allocator`).
> - Macro regimes (`tests/fixtures/allocator_regimes.csv`): real monthly labels from live FRED via
>   `Schwab/research-api/tests/backtest_regime.py --source fred --since 2004-06-01 --csv …`
>   (needs `FRED_API_KEY`; the `~/apps/Schwab/research-api/.env` value has a trailing inline
>   comment — strip everything after `#`, keep the 32 hex chars).
>
> Both committed fixtures carry **no** allocator dependency, so `pytest` stays hermetic on
> numpy/scipy/pandas.
