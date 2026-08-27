from __future__ import annotations

from engine.costs.model import CostModel
from engine.data.store import DataStore
from engine.metrics.core import equity_curve_returns, sharpe_ratio
from engine.strategy.rebalance import RebalanceThrottle
from engine.walkforward.optimizer import StrategyFactory, expand_grid, run_window_backtest


def param_sensitivity(
    store: DataStore,
    symbol: str,
    strategy_factory: StrategyFactory,
    param_grid: dict[str, list],
    start,
    end,
    cost_model: CostModel,
    initial_cash: float = 100_000.0,
) -> list[dict]:
    """Sharpe for every combination in param_grid, each evaluated once
    over the full [start, end] window — a sensitivity surface, not an
    optimizer selection (no train/test split here).
    """
    results = []
    for params in expand_grid(param_grid):
        strategy = strategy_factory(params)
        portfolio = run_window_backtest(
            store, symbol, strategy, start, end, cost_model, initial_cash
        )
        sharpe = sharpe_ratio(equity_curve_returns(portfolio.equity_curve))
        results.append({"params": params, "sharpe": sharpe})
    return results


def rebalance_frequency_sensitivity(
    store: DataStore,
    symbol: str,
    strategy_factory: StrategyFactory,
    base_params: dict,
    frequencies_bars: list[int],
    start,
    end,
    cost_model: CostModel,
    initial_cash: float = 100_000.0,
) -> list[dict]:
    """Sharpe when signals are only allowed through once every N bars,
    for each N in frequencies_bars — how sensitive performance is to how
    often the strategy is allowed to act on its own signal.
    """
    results = []
    for every_n_bars in frequencies_bars:
        throttled = RebalanceThrottle(strategy_factory(base_params), every_n_bars)
        portfolio = run_window_backtest(
            store, symbol, throttled, start, end, cost_model, initial_cash
        )
        sharpe = sharpe_ratio(equity_curve_returns(portfolio.equity_curve))
        results.append({"every_n_bars": every_n_bars, "sharpe": sharpe})
    return results
