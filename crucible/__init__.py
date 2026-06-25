"""CRUCIBLE — a severe test for trading edges. Tells you if your backtest is real."""
from crucible.psr import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    min_track_record_length,
    probabilistic_sharpe_ratio,
)
from crucible.pbo import pbo_cscv
from crucible.regime import PrecomputedRegime, SingleRegime, dominant_regime
from crucible.verdict import RegimeDeflation, Verdict, assess

__all__ = [
    "deflated_sharpe_ratio", "probabilistic_sharpe_ratio", "min_track_record_length",
    "expected_max_sharpe", "pbo_cscv", "assess", "Verdict", "RegimeDeflation",
    "PrecomputedRegime", "SingleRegime", "dominant_regime",
]
__version__ = "0.0.1"
