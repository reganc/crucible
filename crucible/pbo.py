"""
Probability of Backtest Overfitting (PBO) via Combinatorially Symmetric
Cross-Validation (CSCV).

Reference: Bailey, Borwein, López de Prado, Zhu (2015), "The Probability of Backtest
Overfitting."

Input: a (T observations x N trials) matrix of per-period returns — one column per
strategy variant you tried. CSCV asks: when you pick the best variant in-sample, how
often does it land below median out-of-sample? If that happens a lot, your selection
process is overfitting (PBO -> 1). Pure noise gives PBO ~ 0.5+.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from crucible.metrics import sharpe


@dataclass(slots=True)
class PBOReport:
    pbo: float                          # probability of backtest overfitting in [0,1]
    n_trials: int
    n_groups: int                       # S
    n_combinations: int
    logits: list[float] = field(default_factory=list)

    @property
    def overfit(self) -> bool:
        return self.pbo > 0.5


def _metric_per_column(block: np.ndarray, metric_func) -> np.ndarray:
    return np.array([metric_func(block[:, j]) for j in range(block.shape[1])])


def pbo_cscv(returns_matrix: np.ndarray, n_groups: int = 16,
             metric_func=sharpe) -> PBOReport:
    """Compute PBO via CSCV.

    returns_matrix: shape (T, N) — T observations, N trials. N >= 2.
    n_groups (S):   even number of disjoint time blocks. Larger S -> more combinations
                    (C(S, S/2)) and a finer estimate, at higher cost. 16 is a common default.
    """
    M = np.asarray(returns_matrix, dtype=float)
    if M.ndim != 2 or M.shape[1] < 2:
        raise ValueError("returns_matrix must be (T, N) with N >= 2 trials")
    if n_groups % 2 != 0:
        raise ValueError("n_groups (S) must be even")

    T, N = M.shape
    # Partition rows into S contiguous, (near-)equal groups, preserving time order.
    bounds = np.linspace(0, T, n_groups + 1, dtype=int)
    groups = [np.arange(bounds[i], bounds[i + 1]) for i in range(n_groups)]
    all_idx = set(range(n_groups))

    logits: list[float] = []
    for is_combo in combinations(range(n_groups), n_groups // 2):
        is_rows = np.concatenate([groups[g] for g in is_combo])
        oos_rows = np.concatenate([groups[g] for g in sorted(all_idx - set(is_combo))])

        is_perf = _metric_per_column(M[is_rows, :], metric_func)
        oos_perf = _metric_per_column(M[oos_rows, :], metric_func)

        n_star = int(np.argmax(is_perf))                 # best in-sample trial
        # relative rank of the IS-best trial within the OOS performances
        oos_rank = float((oos_perf <= oos_perf[n_star]).sum()) / (N + 1)
        oos_rank = min(max(oos_rank, 1.0 / (N + 1)), N / (N + 1))  # clamp off 0/1
        logits.append(float(np.log(oos_rank / (1.0 - oos_rank))))

    logits_arr = np.array(logits)
    pbo = float((logits_arr <= 0).mean())  # fraction where IS-best is below OOS median
    return PBOReport(pbo=pbo, n_trials=N, n_groups=n_groups,
                     n_combinations=len(logits), logits=logits)
