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


# The ex-regime DSR must be worse than this fraction of equal-sized RANDOM removals for
# the drop to count as genuinely regime-driven rather than a shorter-sample artifact.
REGIME_SPECIFIC_ALPHA = 0.05


@dataclass(slots=True)
class RegimeDeflation:
    """Does the edge survive when you remove the regime it was born in?

    The Deflated-Sharpe drop conflates two effects: the edge genuinely weakening
    (per-period Sharpe falls) and the track record simply getting shorter (fewer
    observations -> lower DSR even with an unchanged edge). The sample-size controls
    separate them:
      - sharpe_full vs sharpe_ex_dominant : per-period, n-independent -> the pure
        effect on the edge's quality.
      - dsr_ex_random_mean / regime_specific_pct : the DSR (and percentile) you'd get
        by removing the SAME NUMBER of observations AT RANDOM. If the real ex-regime
        DSR sits in the left tail (regime_specific_pct small), the collapse is genuinely
        regime-driven; if it sits inside the null, the drop is just a shorter sample.
    """
    dominant_regime: int            # the regime carrying the most positive performance
    dsr_full: float                 # Deflated Sharpe on the whole series
    dsr_ex_dominant: float          # Deflated Sharpe with the dominant regime removed
    sharpe_full: float              # per-period Sharpe, whole series (n-independent)
    sharpe_ex_dominant: float       # per-period Sharpe, dominant regime removed
    n_ex: int                       # observations remaining after removal
    dsr_ex_random_mean: float       # mean DSR over random equal-sized removals (sample-size only)
    regime_specific_pct: float      # percentile of dsr_ex_dominant within that random null
    contributions: dict[int, float]  # summed return per regime

    @property
    def drop(self) -> float:
        return self.dsr_full - self.dsr_ex_dominant

    @property
    def sharpe_drop(self) -> float:
        return self.sharpe_full - self.sharpe_ex_dominant

    @property
    def regime_specific(self) -> bool:
        """The ex-regime DSR is worse than (1 - alpha) of equal-sized random removals —
        i.e. the drop exceeds what sample-size reduction alone would produce."""
        return self.regime_specific_pct < REGIME_SPECIFIC_ALPHA

    @property
    def regime_captive(self) -> bool:
        """A large DSR collapse that is genuinely regime-driven, not a shorter sample."""
        return self.drop >= REGIME_COLLAPSE_DROP and self.regime_specific


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
    regime_boot: int = 1000,
    regime_boot_seed: int = 0,
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
            chosen_arr = np.asarray(chosen_returns, dtype=float)
            ex = chosen_arr[np.asarray(labels) != dom]
            if ex.size >= 2:
                mex = moments(ex)
                dsr_ex = probabilistic_sharpe_ratio(
                    mex["sharpe"], mex["n"], mex["skew"], mex["kurtosis"], sr_benchmark=sr0)
                # Sample-size control: the DSR you'd get by removing the SAME NUMBER of
                # observations at random (no regime structure). If the real ex-regime DSR
                # is in the left tail of this null, the collapse is genuinely regime-driven.
                rng = np.random.default_rng(regime_boot_seed)
                null = np.empty(regime_boot)
                for b in range(regime_boot):
                    ms = moments(rng.choice(chosen_arr, size=mex["n"], replace=False))
                    null[b] = probabilistic_sharpe_ratio(
                        ms["sharpe"], ms["n"], ms["skew"], ms["kurtosis"], sr_benchmark=sr0)
                regime_deflation = RegimeDeflation(
                    dominant_regime=dom, dsr_full=dsr, dsr_ex_dominant=dsr_ex,
                    sharpe_full=m["sharpe"], sharpe_ex_dominant=mex["sharpe"], n_ex=mex["n"],
                    dsr_ex_random_mean=float(null.mean()),
                    regime_specific_pct=float((null <= dsr_ex).mean()),
                    contributions=regime_contributions(chosen_arr, labels))
                rd = regime_deflation
                if rd.regime_captive:
                    notes.append(
                        f"Edge is regime-captive: removing its home regime ({dom}) drops the "
                        f"Deflated Sharpe {dsr:.2f} -> {dsr_ex:.2f} (Δ{rd.drop:.2f}) and the "
                        f"per-period Sharpe {rd.sharpe_full:+.2f} -> {rd.sharpe_ex_dominant:+.2f}. "
                        f"Regime-specific (worse than {100 * (1 - rd.regime_specific_pct):.0f}% of "
                        f"equal-sized random removals), not just a shorter sample.")
                elif rd.drop >= REGIME_COLLAPSE_DROP:
                    notes.append(
                        f"Apparent dependence on regime {dom} is mostly a sample-size effect: the "
                        f"Deflated Sharpe falls {dsr:.2f} -> {dsr_ex:.2f}, but removing any "
                        f"{m['n'] - rd.n_ex} observations does about as much (percentile "
                        f"{rd.regime_specific_pct:.2f}); per-period Sharpe barely moves "
                        f"({rd.sharpe_full:+.2f} -> {rd.sharpe_ex_dominant:+.2f}).")

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
