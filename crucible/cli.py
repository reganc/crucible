"""
CRUCIBLE CLI.

    python -m crucible.cli verdict TRIALS.csv --chosen-col best --n-trials 200
    python -m crucible.cli verdict TRIALS.csv          # uses full matrix, auto n_trials

Where TRIALS.csv is (T rows x N columns) of per-period returns, one column per variant.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from crucible.ingest import load_trial_matrix
from crucible.verdict import assess

_COLOR = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m"}
_RESET = "\033[0m"


def _print_verdict(v) -> None:
    c = _COLOR.get(v.band, "")
    print(f"\n{c}● {v.band.upper()}{_RESET}  {v.headline}\n")
    d = v.deflation
    print(f"  observed Sharpe (per-period) : {d.observed_sharpe:+.4f}")
    print(f"  observations                 : {d.n_obs}")
    print(f"  trials (multiple testing)    : {d.n_trials}")
    print(f"  expected max Sharpe (noise)  : {d.sr_benchmark:+.4f}")
    print(f"  PSR vs 0                      : {d.psr_vs_zero:.3f}")
    print(f"  Deflated Sharpe (DSR)        : {d.deflated_sharpe:.3f}   (want >= 0.95)")
    mtrl = "inf" if d.min_trl == float("inf") else f"{d.min_trl:.0f}"
    print(f"  min track record length      : {mtrl}  (have {d.n_obs})")
    if v.pbo is not None:
        print(f"  PBO (overfit probability)    : {v.pbo.pbo:.3f}   (want < 0.20, "
              f"{v.pbo.n_combinations} CSCV splits)")
    if len(v.regime_sharpe) > 1:
        rs = ", ".join(f"R{r}:{s:+.2f}" for r, s in sorted(v.regime_sharpe.items()))
        print(f"  regime-conditional Sharpe    : {rs}")
    if v.regime_deflation is not None:
        rd = v.regime_deflation
        print(f"  regime-conditional DSR       : full {rd.dsr_full:.3f} -> ex-dominant "
              f"{rd.dsr_ex_dominant:.3f}  (Δ{rd.drop:+.3f}, dominant regime {rd.dominant_regime}, "
              f"n_ex {rd.n_ex})")
        tag = "regime-specific" if rd.regime_specific else "sample-size"
        print(f"  sample-size control          : per-period Sharpe {rd.sharpe_full:+.3f} -> "
              f"{rd.sharpe_ex_dominant:+.3f};  ex-DSR at pct {rd.regime_specific_pct:.2f} of random "
              f"removals (mean {rd.dsr_ex_random_mean:.3f})  [{tag}]")
    for n in v.notes:
        print(f"  ! {n}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crucible")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("verdict", help="assess whether an edge is real")
    pv.add_argument("trials_csv", help="(T x N) per-period returns CSV")
    pv.add_argument("--chosen-col", default=None,
                    help="column name of the chosen strategy (default: best in-sample)")
    pv.add_argument("--n-trials", type=int, default=None,
                    help="multiple-testing count (default: number of columns)")
    pv.add_argument("--pbo-groups", type=int, default=16)

    args = parser.parse_args(argv)

    if args.cmd == "verdict":
        M = load_trial_matrix(args.trials_csv)
        n_trials = args.n_trials or M.shape[1]
        if args.chosen_col is not None:
            import pandas as pd
            cols = list(pd.read_csv(args.trials_csv).columns)
            if cols[0].lower() in ("date", "time", "timestamp", "index", "unnamed: 0"):
                cols = cols[1:]
            chosen = M[:, cols.index(args.chosen_col)]
        else:
            from crucible.metrics import sharpe
            chosen = M[:, int(np.argmax([sharpe(M[:, j]) for j in range(M.shape[1])]))]

        v = assess(chosen, n_trials=n_trials, trials_matrix=M, pbo_groups=args.pbo_groups)
        _print_verdict(v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
