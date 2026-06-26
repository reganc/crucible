"""Run CRUCIBLE's verdict on the real allocator export WITH the real macro
six-regime classifier wired in — surfacing regime-conditional Deflated Sharpe (Task 2).

    python examples/verdict_allocator_regime.py

Both inputs are committed real fixtures: the allocator's 18-strategy backtest export
and the research-api macro classifier's monthly regime labels (live FRED, 2004-2026).
"""
from __future__ import annotations

from pathlib import Path

from crucible.cli import _print_verdict
from crucible.ingest import load_allocator, allocator_regime_classifier
from crucible.verdict import assess

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
EXPORT = FIXTURES / "allocator_export.csv"
REGIMES = FIXTURES / "allocator_regimes.csv"


def main() -> int:
    trials, chosen = load_allocator(str(EXPORT))
    classifier = allocator_regime_classifier(str(EXPORT), str(REGIMES))
    verdict = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials, regime=classifier)
    _print_verdict(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
