"""Task 2 integration — the real Schwab macro classifier wired through assess().

Uses two committed real fixtures: the allocator's 27-variant export and the
research-api macro classifier's monthly labels (live FRED, 2004-2026). Hermetic:
reads CSVs only — no Schwab import, no network. Asserts the real-classifier path
produces a well-formed regime-conditional deflation; it does not assert a band or
exact numbers (the tool reports what the data says).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from crucible.ingest import load_schwab, schwab_regime_classifier
from crucible.verdict import assess

FIXTURES = Path(__file__).parent / "fixtures"
EXPORT = FIXTURES / "schwab_export.csv"
REGIMES = FIXTURES / "schwab_regimes.csv"


def test_regime_classifier_aligns_to_returns():
    _, chosen = load_schwab(str(EXPORT))
    clf = schwab_regime_classifier(str(EXPORT), str(REGIMES))
    labels = clf.label(chosen)
    assert labels.shape[0] == chosen.shape[0]          # date-aligned, one label per obs
    assert clf.n_regimes > 1                            # multiple macro regimes spanned
    assert set(np.unique(labels)).issubset(set(range(-1, 6)))   # mapped to the macro id space


def test_regime_conditional_deflation_present_and_wellformed():
    trials, chosen = load_schwab(str(EXPORT))
    clf = schwab_regime_classifier(str(EXPORT), str(REGIMES))
    v = assess(chosen, n_trials=trials.shape[1], trials_matrix=trials, pbo_groups=10, regime=clf)

    assert v.regime_deflation is not None               # real classifier + >1 regime
    rd = v.regime_deflation
    assert 0.0 <= rd.dsr_full <= 1.0
    assert 0.0 <= rd.dsr_ex_dominant <= 1.0
    assert 0 <= rd.dominant_regime <= 5
    assert 0 < rd.n_ex < chosen.shape[0]
