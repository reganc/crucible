"""Show the regime-captive detector firing on real data.

Two committed real fixtures, same macro six-regime classifier:
  - the allocator's diversified book — regime-robust (broadly positive across regimes),
  - a raw small-cap holding (IWM) — regime-captive: its Deflated Sharpe collapses when
    its home regime (the long disinflation bull) is removed.

    python examples/verdict_regime_captive.py
"""
from __future__ import annotations

from pathlib import Path

from crucible.cli import _print_verdict
from crucible.ingest import allocator_regime_classifier, load_allocator
from crucible.verdict import assess

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
REGIMES = FIXTURES / "allocator_regimes.csv"


def _run(export: Path, label: str) -> None:
    trials, chosen = load_allocator(str(export))
    clf = allocator_regime_classifier(str(export), str(REGIMES))
    print(f"\n=== {label} ===")
    _print_verdict(assess(chosen, n_trials=trials.shape[1], trials_matrix=trials, regime=clf))


def main() -> int:
    _run(FIXTURES / "allocator_export.csv", "allocator diversified book — regime-robust")
    _run(FIXTURES / "cyclicals_export.csv", "raw small-cap holding (IWM) — regime-captive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
