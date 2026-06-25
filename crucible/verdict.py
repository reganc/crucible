"""
The verdict — the actual product. Turns the statistical primitives into one honest
answer: is this edge real, or is it the best of N noisy tries?

This is the orchestration layer the research identified as the white space: the stats
exist, but nobody packages them into a single defensible verdict that consumes your
backtest output and refuses to flatter you.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from crucible.metrics import moments
from crucible.pbo import PBOReport, pbo_cscv
from crucible.psr import (
    DeflationReport,
    deflated_sharpe_ratio,
    min_track_record_length,
    probabilistic_sharpe_ratio,
)
from crucible.regime import (
    RegimeClassifier,
    SingleRegime,
    dominant_regime,
    regime_conditional_sharpe,
    regime_contributions,
)

# A drop this large in the Deflated Sharpe when the home regime is removed means the
# edge is regime-captive — it largely does not survive without that regime.
REGIME_COLLAPSE_DROP = 0.5


@dataclass(slots=True)
class RegimeDeflation:
    """Does the edge survive when you remove the regime it was born in?"""
    dominant_regime: int            # the regime carrying the most positive performance
    dsr_full: float                 # Deflated Sharpe on the whole series
    dsr_ex_dominant: float          # Deflated Sharpe with the dominant regime removed
    n_ex: int                       # observations remaining after removal
    contributions: dict[int, float]  # summed return per regime

    @property
    def drop(self) -> float:
        return self.dsr_full - self.dsr_ex_dominant

    @property
    def regime_captive(self) -> bool:
        return self.drop >= REGIME_COLLAPSE_DROP


@dataclass(slots=True)
class Verdict:
    band: str                       # "green" | "yellow" | "red"
    headline: str
    deflation: DeflationReport
    pbo: PBOReport | None
    regime_sharpe: dict[int, float] = field(default_factory=dict)
    regime_deflation: RegimeDeflation | None = None
    notes: list[str] = field(default_factory=list)


def assess(
    chosen_returns: np.ndarray,
    *,
    n_trials: int,
    trials_matrix: np.ndarray | None = None,
    sr_variance: float | None = None,
    pbo_groups: int = 16,
    regime: RegimeClassifier | None = None,
) -> Verdict:
    """Produce a single honest verdict on a chosen strategy.

    chosen_returns : per-period returns of the strategy you selected.
    n_trials       : how many variants you tried to find it (the multiple-testing count).
    trials_matrix  : optional (T x N) returns of all trials -> enables PBO + sr_variance.
    sr_variance    : variance of trial Sharpes; derived from trials_matrix if omitted.
    """
    m = moments(chosen_returns)
    notes: list[str] = []

    # Deflation inputs
    if sr_variance is None and trials_matrix is not None:
        from crucible.ingest import trial_sharpe_variance
        sr_variance = trial_sharpe_variance(trials_matrix)
    if sr_variance is None:
        sr_variance = 0.0
        notes.append("No trial-Sharpe variance supplied; DSR deflation is weak. "
                     "Pass trials_matrix or sr_variance for a real deflation.")

    dsr = deflated_sharpe_ratio(m["sharpe"], m["n"], m["skew"], m["kurtosis"],
                                sr_variance=sr_variance, n_trials=n_trials)
    psr0 = probabilistic_sharpe_ratio(m["sharpe"], m["n"], m["skew"], m["kurtosis"])
    mtrl = min_track_record_length(m["sharpe"], m["skew"], m["kurtosis"])
    from crucible.psr import expected_max_sharpe
    sr0 = expected_max_sharpe(sr_variance, n_trials)

    deflation = DeflationReport(
        observed_sharpe=m["sharpe"], n_obs=m["n"], n_trials=n_trials, sr_benchmark=sr0,
        psr_vs_zero=psr0, deflated_sharpe=dsr, min_trl=mtrl,
        skew=m["skew"], kurtosis=m["kurtosis"],
    )

    # PBO (needs the full trial matrix)
    pbo_report: PBOReport | None = None
    if trials_matrix is not None and np.asarray(trials_matrix).shape[1] >= 2:
        try:
            pbo_report = pbo_cscv(trials_matrix, n_groups=pbo_groups)
        except ValueError as e:
            notes.append(f"PBO skipped: {e}")

    # Regime-conditional sharpe
    clf = regime or SingleRegime()
    labels = clf.label(chosen_returns)
    regime_sr = regime_conditional_sharpe(chosen_returns, labels)
    if len(regime_sr) > 1:
        pos = [r for r, s in regime_sr.items() if s > 0]
        if len(pos) == 1:
            notes.append(f"Edge appears concentrated in regime {pos[0]} — check regime "
                         f"dependence before trusting it out of sample.")

    # Regime-conditional deflation: does the edge survive without its home regime?
    # Only when a real classifier is supplied AND more than one regime is present.
    regime_deflation: RegimeDeflation | None = None
    if regime is not None and len(regime_sr) > 1:
        dom = dominant_regime(chosen_returns, labels)
        if dom is not None:
            ex = np.asarray(chosen_returns, dtype=float)[np.asarray(labels) != dom]
            if ex.size >= 2:
                mex = moments(ex)
                dsr_ex = probabilistic_sharpe_ratio(
                    mex["sharpe"], mex["n"], mex["skew"], mex["kurtosis"], sr_benchmark=sr0)
                regime_deflation = RegimeDeflation(
                    dominant_regime=dom, dsr_full=dsr, dsr_ex_dominant=dsr_ex, n_ex=mex["n"],
                    contributions=regime_contributions(chosen_returns, labels))
                if regime_deflation.regime_captive:
                    notes.append(
                        f"Edge is regime-captive: removing its home regime ({dom}) drops the "
                        f"Deflated Sharpe {dsr:.2f} -> {dsr_ex:.2f} (Δ{regime_deflation.drop:.2f}). "
                        f"It largely does not survive out of that regime.")

    band, headline = _band(deflation, pbo_report)
    return Verdict(band=band, headline=headline, deflation=deflation, pbo=pbo_report,
                   regime_sharpe=regime_sr, regime_deflation=regime_deflation, notes=notes)


def _band(d: DeflationReport, p: PBOReport | None) -> tuple[str, str]:
    pbo_bad = p is not None and p.pbo > 0.5
    pbo_warn = p is not None and 0.2 < p.pbo <= 0.5

    if d.deflated_sharpe < 0.90 or pbo_bad:
        return "red", ("Likely overfit. After accounting for how many variants you tried, "
                       "this edge is not convincingly better than luck.")
    if d.deflated_sharpe < 0.95 or pbo_warn or d.n_obs < d.min_trl:
        return "yellow", ("Inconclusive. The edge is plausible but not established — "
                          "more out-of-sample data or fewer trials would settle it.")
    return "green", ("Survives deflation. The edge clears the expected-max-Sharpe "
                     "benchmark for the number of trials, with low overfitting probability.")
