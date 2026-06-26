"""Task 2 on real data — the regime-captive detector fires on a genuinely regime-
dependent holding and stays quiet on the regime-robust allocator book.

Hermetic: two committed real fixtures + the macro-regime fixture, no allocator import,
no network. This is the real-data counterpart to the synthetic cases in test_regime.py.
"""
from __future__ import annotations

from pathlib import Path

from crucible.ingest import allocator_regime_classifier, load_allocator
from crucible.verdict import assess

FIXTURES = Path(__file__).parent / "fixtures"
REGIMES = FIXTURES / "allocator_regimes.csv"


def _assess(export_name: str):
    export = FIXTURES / export_name
    trials, chosen = load_allocator(str(export))
    clf = allocator_regime_classifier(str(export), str(REGIMES))
    return assess(chosen, n_trials=trials.shape[1], trials_matrix=trials, pbo_groups=10, regime=clf)


def test_raw_cyclical_holding_is_regime_captive():
    # chosen = IWM (US small caps): edge concentrated in the disinflation bull.
    v = _assess("cyclicals_export.csv")
    rd = v.regime_deflation
    assert rd is not None
    assert rd.regime_captive                            # DSR drop >= 0.5 without its home regime
    assert rd.dsr_ex_dominant < rd.dsr_full
    assert any("regime-captive" in n for n in v.notes)


def test_allocator_book_is_not_regime_captive():
    # the diversified allocator book is broadly positive across regimes by design.
    v = _assess("allocator_export.csv")
    rd = v.regime_deflation
    assert rd is not None
    assert not rd.regime_captive
