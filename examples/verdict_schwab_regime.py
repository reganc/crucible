"""Run CRUCIBLE's verdict on the real Schwab allocator export WITH the real macro
six-regime classifier wired in — surfacing regime-conditional Deflated Sharpe (Task 2).

    python examples/verdict_schwab_regime.py

Both inputs are committed real fixtures: the allocator's 27-variant backtest export
and the research-api macro classifier's monthly regime labels (live FRED, 2004-2026).
"""
from __future__ import annotations

from pathlib import Path

from crucible.cli import _print_verdict
from crucible.ingest import load_schwab, schwab_regime_classifier
from crucible.verdict import assess

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
EXPORT = FIXTURES / "schwab_export.csv"
REGIMES = FIXTURES / "schwab_regimes.csv"


def main() -> int:
    trials, chosen = load_schwab(str(EXPORT))
    classifier = schwab_regime_classifier(str(EXPORT), str(REGIMES))
    verdict = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials, regime=classifier)
    _print_verdict(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
