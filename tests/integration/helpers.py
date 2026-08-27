from __future__ import annotations

import math
from datetime import datetime, timedelta

import pandas as pd
from engine.costs.model import CostModel
from engine.data.handler import DataHandler
from engine.data.store import DataStore
from engine.events.loop import run_backtest
from engine.events.stream import build_market_event_queue
from engine.execution.handler import ExecutionHandler
from engine.portfolio.portfolio import Portfolio
from engine.strategy.sma_crossover import SMACrossoverStrategy

SYMBOL = "AAA"


def synthetic_prices(n: int = 120) -> list[float]:
    # Oscillation on top of a mild uptrend -> several SMA(5,20) crossovers.
    return [100.0 + 10 * math.sin(i / 5) + 0.15 * i for i in range(n)]


def seed_store(prices: list[float]) -> DataStore:
    store = DataStore(":memory:")
    base = datetime(2020, 1, 1)
    ts = [base + timedelta(days=i) for i in range(len(prices))]
    df = pd.DataFrame(
        {
            "symbol": SYMBOL,
            "ts": ts,
            "knowledge_ts": ts,
            "open": prices,
            "high": [p * 1.001 for p in prices],
            "low": [p * 0.999 for p in prices],
            "close": prices,
            "volume": 1_000_000.0,
            "source": "test",
        }
    )
    store.insert_raw_prices(df)
    return store


def run_full_backtest(cost_model: CostModel, prices: list[float] | None = None) -> Portfolio:
    store = seed_store(prices if prices is not None else synthetic_prices())
    data_handler = DataHandler(store)
    strategy = SMACrossoverStrategy(symbol=SYMBOL, short_window=5, long_window=20)
    portfolio = Portfolio(store, initial_cash=100_000.0, target_weight=1.0)
    execution = ExecutionHandler(data_handler, cost_model)
    queue = build_market_event_queue(store, [SYMBOL])
    return run_backtest(queue, data_handler, strategy, portfolio, execution)


def sharpe(equity_curve: list[tuple]) -> float:
    equities = pd.Series([e for _, e in equity_curve])
    returns = equities.pct_change().dropna()
    if returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std())
