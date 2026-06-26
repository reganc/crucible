"""Run CRUCIBLE's verdict on the committed real allocator export.

    python examples/verdict_allocator.py

Demonstrates Task 1 end to end: the engine-specific export is read by the
ingest adapter, and the generic verdict scores the registered-primary strategy
against the 18 strategies that were tried to find it.
"""
from __future__ import annotations

from pathlib import Path

from crucible.cli import _print_verdict
from crucible.ingest import load_allocator
from crucible.verdict import assess

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "allocator_export.csv"


def main() -> int:
    trials, chosen = load_allocator(str(FIXTURE))
    verdict = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials)
    _print_verdict(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
