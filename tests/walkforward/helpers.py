from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from engine.data.store import DataStore
from engine.strategy.sma_crossover import SMACrossoverStrategy

SYMBOL = "AAA"


def seed_store(
    prices: list[float], symbol: str = SYMBOL, start: datetime | None = None
) -> DataStore:
    store = DataStore(":memory:")
    base = start or datetime(2020, 1, 1)
    ts = [base + timedelta(days=i) for i in range(len(prices))]
    df = pd.DataFrame(
        {
            "symbol": symbol,
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
    return store, ts


def sma_factory(params: dict):
    return SMACrossoverStrategy(symbol=SYMBOL, **params)
