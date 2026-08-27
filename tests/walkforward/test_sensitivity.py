import math

from engine.costs.model import ZERO_COST_MODEL
from engine.metrics.core import equity_curve_returns, sharpe_ratio
from engine.walkforward.optimizer import run_window_backtest
from engine.walkforward.sensitivity import param_sensitivity, rebalance_frequency_sensitivity

from tests.walkforward.helpers import SYMBOL, seed_store, sma_factory


def _oscillating_prices(n=120):
    return [100.0 + 10 * math.sin(i / 5) + 0.1 * i for i in range(n)]


def test_param_sensitivity_covers_the_full_grid():
    store, ts = seed_store(_oscillating_prices())
    grid = {"short_window": [3, 5], "long_window": [15, 20]}

    results = param_sensitivity(store, SYMBOL, sma_factory, grid, ts[0], ts[-1], ZERO_COST_MODEL)

    assert len(results) == 4
    assert {r["params"]["short_window"] for r in results} == {3, 5}
    assert all(isinstance(r["sharpe"], float) for r in results)


def test_rebalance_frequency_sensitivity_covers_all_requested_frequencies():
    store, ts = seed_store(_oscillating_prices())
    base_params = {"short_window": 5, "long_window": 20}

    results = rebalance_frequency_sensitivity(
        store, SYMBOL, sma_factory, base_params, [1, 3, 5, 10], ts[0], ts[-1], ZERO_COST_MODEL
    )

    assert [r["every_n_bars"] for r in results] == [1, 3, 5, 10]
    assert all(isinstance(r["sharpe"], float) for r in results)


def test_rebalance_frequency_of_1_matches_the_untouched_strategy():
    """every_n_bars=1 lets every signal through — should reproduce running
    the strategy directly, unthrottled.
    """
    store, ts = seed_store(_oscillating_prices())
    base_params = {"short_window": 5, "long_window": 20}

    throttled_results = rebalance_frequency_sensitivity(
        store, SYMBOL, sma_factory, base_params, [1], ts[0], ts[-1], ZERO_COST_MODEL
    )
    direct_portfolio = run_window_backtest(
        store, SYMBOL, sma_factory(base_params), ts[0], ts[-1], ZERO_COST_MODEL
    )
    direct_sharpe = sharpe_ratio(equity_curve_returns(direct_portfolio.equity_curve))
    assert throttled_results[0]["sharpe"] == direct_sharpe
