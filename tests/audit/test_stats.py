import numpy as np
import pandas as pd
from engine.audit.stats import deflated_sharpe_ratio, pbo_cscv


def test_deflated_sharpe_flags_a_lucky_winner_among_many_noise_trials():
    """50 pure-noise (zero true edge) strategies; whichever one happens to
    have the best in-sample Sharpe is by construction just noise. DSR,
    correcting for the 50 trials, must not endorse it as genuine skill.
    """
    rng = np.random.default_rng(42)
    n_trials, n_obs = 50, 120
    trial_returns = rng.normal(loc=0.0, scale=0.01, size=(n_obs, n_trials))
    trial_sharpes = trial_returns.mean(axis=0) / trial_returns.std(axis=0, ddof=1)

    best_idx = int(np.argmax(trial_sharpes))
    best_returns = pd.Series(trial_returns[:, best_idx])

    result = deflated_sharpe_ratio(best_returns, list(trial_sharpes))

    assert result["observed_sharpe"] > 0  # looks good naively...
    assert result["dsr"] < 0.95  # ...but isn't endorsed once corrected for 50 trials


def test_deflated_sharpe_does_not_penalize_a_single_genuinely_skillful_trial():
    """A single trial (no multiple-testing exposure) with a real, modest
    edge should NOT be crushed by the deflation the way the lucky-winner
    case is — this is the contrast case proving DSR discriminates rather
    than just always reporting low.
    """
    rng = np.random.default_rng(7)
    n_obs = 1000
    returns = pd.Series(rng.normal(loc=0.003, scale=0.01, size=n_obs))

    result = deflated_sharpe_ratio(returns, [float(returns.mean() / returns.std(ddof=1))])

    assert result["dsr"] > 0.95


def test_pbo_flags_overfitting_when_selection_is_pure_noise():
    """N pure-noise strategies: whichever looks best in a given in-sample
    block is essentially a coin flip on how it ranks out-of-sample. PBO
    should sit well above the near-zero level a genuinely skillful panel
    would produce.
    """
    rng = np.random.default_rng(123)
    t, n = 400, 12
    returns_matrix = rng.normal(loc=0.0, scale=0.01, size=(t, n))

    result = pbo_cscv(returns_matrix, n_splits=8)

    assert result["pbo"] > 0.4
    assert result["n_combinations"] > 0


def test_pbo_is_low_when_one_strategy_has_a_persistent_genuine_edge():
    """Contrast case: one strategy has a real, consistent edge across the
    whole sample (not just a lucky subset), the rest are noise. The
    in-sample winner should usually be that same strategy, and it should
    keep ranking well out-of-sample too -> low PBO.
    """
    rng = np.random.default_rng(99)
    t, n = 400, 12
    returns_matrix = rng.normal(loc=0.0, scale=0.01, size=(t, n))
    returns_matrix[:, 0] = rng.normal(
        loc=0.004, scale=0.01, size=t
    )  # persistent edge, not a boundary artifact

    result = pbo_cscv(returns_matrix, n_splits=8)

    assert result["pbo"] < 0.3
