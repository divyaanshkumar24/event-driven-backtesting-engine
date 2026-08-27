from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

_EULER_MASCHERONI = 0.5772156649015329


def expected_max_sharpe_under_null(trial_sharpes: list[float]) -> float:
    """E[max Sharpe] achievable by chance alone, given `len(trial_sharpes)`
    independent trials with the empirically observed spread of Sharpes
    (Bailey & Lopez de Prado's benchmark for the Deflated Sharpe Ratio).
    """
    n = len(trial_sharpes)
    if n <= 1:
        return 0.0
    sigma_sr = float(np.std(trial_sharpes, ddof=1))
    if sigma_sr == 0:
        return 0.0
    z1 = stats.norm.ppf(1 - 1.0 / n)
    z2 = stats.norm.ppf(1 - 1.0 / (n * math.e))
    return sigma_sr * ((1 - _EULER_MASCHERONI) * z1 + _EULER_MASCHERONI * z2)


def probabilistic_sharpe_ratio(
    observed_sharpe: float, benchmark_sharpe: float, n_obs: int, skew: float, kurtosis: float
) -> float:
    """P(true Sharpe > benchmark_sharpe), accounting for the sample length
    and the non-normality (skew/kurtosis) of returns. `kurtosis` is
    non-excess (normal == 3), matching the PSR/DSR literature's convention.
    """
    if n_obs <= 1:
        return 0.5
    denom = 1 - skew * observed_sharpe + (kurtosis - 1) / 4 * observed_sharpe**2
    if denom <= 0:
        denom = 1e-12
    z = (observed_sharpe - benchmark_sharpe) * (n_obs - 1) ** 0.5 / denom**0.5
    return float(stats.norm.cdf(z))


def deflated_sharpe_ratio(observed_returns: pd.Series, trial_sharpes: list[float]) -> dict:
    """DSR: the probability the observed strategy's Sharpe reflects genuine
    skill once corrected for having tried `len(trial_sharpes)` param
    combinations. A high naive Sharpe from a strategy that was one of many
    trials should deflate toward 0.5 (indistinguishable from luck).
    """
    n_obs = len(observed_returns)
    std = float(observed_returns.std(ddof=1)) if n_obs > 1 else 0.0
    observed_sharpe = float(observed_returns.mean() / std) if std else 0.0
    skew = float(stats.skew(observed_returns)) if n_obs > 2 else 0.0
    kurtosis = float(stats.kurtosis(observed_returns, fisher=False)) if n_obs > 2 else 3.0

    benchmark = expected_max_sharpe_under_null(trial_sharpes)
    dsr = probabilistic_sharpe_ratio(observed_sharpe, benchmark, n_obs, skew, kurtosis)

    return {
        "dsr": dsr,
        "observed_sharpe": observed_sharpe,
        "benchmark_sharpe_under_null": benchmark,
        "n_trials": len(trial_sharpes),
        "n_obs": n_obs,
    }


def _column_sharpe(returns: np.ndarray) -> np.ndarray:
    mean = returns.mean(axis=0)
    std = returns.std(axis=0, ddof=1)
    std = np.where(std == 0, 1e-12, std)
    return mean / std


def pbo_cscv(returns_matrix: np.ndarray, n_splits: int = 8) -> dict:
    """Probability of Backtest Overfitting via Combinatorially Symmetric
    Cross-Validation (Bailey, Borwein, Lopez de Prado & Zhu).

    returns_matrix: T x N array (T periods, N param combinations). Split T
    into `n_splits` contiguous blocks; for every way of picking half the
    blocks as "IS" and the rest as "OOS", find the IS-best combination and
    check whether it ranks below the OOS median. PBO is the fraction of
    splits where it does — a high PBO means whichever combo looks best
    in-sample is little better than a coin flip out-of-sample.
    """
    if n_splits % 2 != 0:
        raise ValueError("n_splits must be even")
    t, n = returns_matrix.shape
    block_size = t // n_splits
    if block_size == 0:
        raise ValueError("not enough observations for the requested number of splits")
    # Any trailing remainder past block_size * n_splits is dropped so every
    # block stays equal-sized, which CSCV requires.
    blocks = [returns_matrix[i * block_size : (i + 1) * block_size] for i in range(n_splits)]

    half = n_splits // 2
    all_indices = set(range(n_splits))
    logits = []

    for is_choice in combinations(range(n_splits), half):
        is_indices = set(is_choice)
        oos_indices = sorted(all_indices - is_indices)

        is_returns = np.concatenate([blocks[i] for i in sorted(is_indices)], axis=0)
        oos_returns = np.concatenate([blocks[i] for i in oos_indices], axis=0)

        is_sharpe = _column_sharpe(is_returns)
        oos_sharpe = _column_sharpe(oos_returns)

        best_n = int(np.argmax(is_sharpe))
        rank = float(np.mean(oos_sharpe <= oos_sharpe[best_n]))
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(math.log(rank / (1 - rank)))

    logits_arr = np.array(logits)
    return {
        "pbo": float(np.mean(logits_arr <= 0)),
        "n_combinations": len(logits_arr),
        "mean_logit": float(logits_arr.mean()),
        "n_splits": n_splits,
    }
