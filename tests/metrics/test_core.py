from datetime import datetime, timedelta

import pandas as pd
import pytest
from engine.metrics.core import (
    calmar_ratio,
    equity_curve_returns,
    max_drawdown,
    max_drawdown_duration,
    sortino_ratio,
)


def _curve(values):
    base = datetime(2020, 1, 1)
    return [(base + timedelta(days=i), v) for i, v in enumerate(values)]


def test_max_drawdown_on_a_simple_peak_and_trough():
    curve = _curve([100, 110, 88, 90, 121])  # peak 110 -> trough 88 = -20%
    assert max_drawdown(curve) == pytest.approx(-0.2)


def test_max_drawdown_is_zero_for_a_monotonic_series():
    curve = _curve([100, 105, 110, 120])
    assert max_drawdown(curve) == 0.0


def test_max_drawdown_duration_recovered_within_sample():
    # peak at idx1 (110), recovers to a new high (111) at idx4 -> 3 bars elapsed
    curve = _curve([100, 110, 95, 100, 111])
    result = max_drawdown_duration(curve)
    assert result["bars"] == 3
    assert result["censored"] is False


def test_max_drawdown_duration_still_underwater_at_end_is_censored():
    # peak at idx1 (120), never recovers -> elapsed to the last bar (idx3) = 2
    curve = _curve([100, 120, 90, 95])
    result = max_drawdown_duration(curve)
    assert result["bars"] == 2
    assert result["censored"] is True


def test_max_drawdown_duration_empty_or_single_point():
    assert max_drawdown_duration([]) == {"bars": 0, "censored": False}
    assert max_drawdown_duration(_curve([100])) == {"bars": 0, "censored": False}


def test_sortino_ignores_upside_dispersion_holding_mean_and_downside_fixed():
    # Same downside values and same overall mean in both series, but the
    # upside values are dispersed differently. Sortino's denominator only
    # looks at downside, so it must come out identical despite the very
    # different upside variance (unlike Sharpe, which would differ).
    same_downside = [-0.01, -0.01, -0.01]
    even_upside = pd.Series(same_downside + [0.02, 0.02, 0.02])
    dispersed_upside = pd.Series(same_downside + [0.0, 0.02, 0.04])
    assert even_upside.mean() == dispersed_upside.mean()
    assert sortino_ratio(even_upside) == sortino_ratio(dispersed_upside)


def test_sortino_is_zero_when_no_downside_exists():
    all_positive = pd.Series([0.01, 0.02, 0.01, 0.03])
    assert sortino_ratio(all_positive) == 0.0


def test_calmar_ratio_positive_return_over_drawdown():
    curve = _curve([100.0 * (1.001**i) for i in range(300)])  # smooth uptrend, ~no drawdown
    returns = equity_curve_returns(curve)
    result = calmar_ratio(returns, curve)
    assert result >= 0
