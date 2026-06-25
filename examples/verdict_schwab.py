"""Run CRUCIBLE's verdict on the committed real Schwab allocator export.

    python examples/verdict_schwab.py

Demonstrates Task 1 end to end: the engine-specific export is read by the
ingest adapter, and the generic verdict scores the registered-primary strategy
against the 27 variants that were tried to find it.
"""
from __future__ import annotations

from pathlib import Path

from crucible.cli import _print_verdict
from crucible.ingest import load_schwab
from crucible.verdict import assess

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "schwab_export.csv"


def main() -> int:
    trials, chosen = load_schwab(str(FIXTURE))
    verdict = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials)
    _print_verdict(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
