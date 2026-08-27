from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import product

from engine.costs.model import CostModel
from engine.data.handler import DataHandler
from engine.data.store import DataStore
from engine.events.loop import run_backtest
from engine.events.stream import build_market_event_queue
from engine.execution.handler import ExecutionHandler
from engine.metrics.core import equity_curve_returns, sharpe_ratio
from engine.portfolio.portfolio import Portfolio
from engine.strategy.base import Strategy

StrategyFactory = Callable[[dict], Strategy]


@dataclass(frozen=True)
class Trial:
    params: dict
    sharpe: float
    portfolio: Portfolio


def expand_grid(param_grid: dict[str, list]) -> list[dict]:
    keys = list(param_grid)
    if not keys:
        return [{}]
    return [
        dict(zip(keys, values, strict=True)) for values in product(*(param_grid[k] for k in keys))
    ]


def run_window_backtest(
    store: DataStore,
    symbol: str,
    strategy: Strategy,
    start,
    end,
    cost_model: CostModel,
    initial_cash: float = 100_000.0,
) -> Portfolio:
    """Runs a fresh backtest restricted to bars in [start, end]. The
    DataHandler's replay clock never advances past `end`, so as_of() calls
    during this run cannot see anything outside the window either — this
    is what makes purge/embargo enforcement structural rather than a
    post-hoc filter.
    """
    data_handler = DataHandler(store)
    portfolio = Portfolio(store, initial_cash=initial_cash)
    execution = ExecutionHandler(data_handler, cost_model)
    queue = build_market_event_queue(store, [symbol], start=start, end=end)
    return run_backtest(queue, data_handler, strategy, portfolio, execution)


def optimize_in_sample(
    store: DataStore,
    symbol: str,
    strategy_factory: StrategyFactory,
    param_grid: dict[str, list],
    start,
    end,
    cost_model: CostModel,
    initial_cash: float = 100_000.0,
) -> tuple[Trial, list[Trial]]:
    """Grid search over param_grid, scored by Sharpe on [start, end] only.
    Returns the best trial plus every trial, since the full set of trial
    Sharpes is what the bias auditor needs for the deflation/PBO stats.
    """
    trials = []
    for params in expand_grid(param_grid):
        strategy = strategy_factory(params)
        portfolio = run_window_backtest(
            store, symbol, strategy, start, end, cost_model, initial_cash
        )
        returns = equity_curve_returns(portfolio.equity_curve)
        trials.append(Trial(params=params, sharpe=sharpe_ratio(returns), portfolio=portfolio))

    best = max(trials, key=lambda t: t.sharpe)
    return best, trials
