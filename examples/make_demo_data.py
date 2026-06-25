"""
Generate demo trial matrices to exercise the verdict:

  noise_trials.csv : N random strategies, no real edge. Picking the best in-sample
                     SHOULD be flagged red (high PBO, low DSR).
  real_trials.csv  : the same, plus one column with a genuine small positive drift.

    python examples/make_demo_data.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

T, N = 1000, 50  # 1000 periods, 50 variants

# Pure noise: every trial is mean-zero. The best in-sample is luck.
noise = rng.normal(0.0, 0.01, size=(T, N))
pd.DataFrame(noise, columns=[f"v{j}" for j in range(N)]).to_csv("noise_trials.csv", index=False)

# Real edge: same noise, but replace one column with a genuine positive Sharpe.
real = noise.copy()
real[:, 0] = rng.normal(0.002, 0.01, size=T)  # ~3 annualized Sharpe, clearly real
pd.DataFrame(real, columns=[f"v{j}" for j in range(N)]).to_csv("real_trials.csv", index=False)

print("wrote noise_trials.csv and real_trials.csv  (shape %dx%d)" % (T, N))
