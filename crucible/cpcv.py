"""
Combinatorial Purged Cross-Validation seam.

Per the research, CPCV is the import-don't-build piece: skfolio ships a maintained,
scikit-learn-native implementation. This module is a thin seam so the rest of CRUCIBLE
depends on a stable interface, not on skfolio's API directly — and so the package still
imports and runs (PSR/DSR/PBO) even when skfolio isn't installed.

Install with:  pip install skfolio
"""
from __future__ import annotations


def combinatorial_purged_cv(n_folds: int = 10, n_test_folds: int = 8,
                            purged_size: int = 0, embargo_size: int = 0):
    """Return a skfolio CombinatorialPurgedCV splitter.

    n_folds (N) and n_test_folds (k) control the number of backtest paths:
    paths = C(N, k) * k / N. Purge removes train samples whose label horizon overlaps
    the test period; embargo drops observations right after each test block.
    """
    try:
        from skfolio.model_selection import CombinatorialPurgedCV
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "CPCV requires skfolio. Install it with `pip install skfolio`. "
            "PSR/DSR/PBO work without it."
        ) from e
    return CombinatorialPurgedCV(
        n_folds=n_folds, n_test_folds=n_test_folds,
        purged_size=purged_size, embargo_size=embargo_size,
    )


def available() -> bool:
    try:
        import skfolio  # noqa: F401
        return True
    except ImportError:
        return False
