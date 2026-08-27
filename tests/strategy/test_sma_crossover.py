from datetime import datetime, timedelta

import pandas as pd
from engine.data.handler import DataHandler
from engine.data.store import DataStore
from engine.events.event import Direction, MarketEvent
from engine.strategy.sma_crossover import SMACrossoverStrategy


def _seed_store(prices):
    store = DataStore(":memory:")
    base = datetime(2020, 1, 1)
    ts = [base + timedelta(days=i) for i in range(len(prices))]
    df = pd.DataFrame(
        {
            "symbol": "AAA",
            "ts": ts,
            "knowledge_ts": ts,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": 1_000_000.0,
            "source": "test",
        }
    )
    store.insert_raw_prices(df)
    return store, ts


def test_no_signal_until_long_window_is_filled():
    prices = [100.0] * 10
    store, ts = _seed_store(prices)
    data_handler = DataHandler(store)
    strategy = SMACrossoverStrategy(symbol="AAA", short_window=3, long_window=5)

    for i, t in enumerate(ts):
        data_handler.advance_to(t)
        signal = strategy.on_market_event(
            MarketEvent(
                timestamp=t,
                symbol="AAA",
                open=prices[i],
                high=prices[i],
                low=prices[i],
                close=prices[i],
                volume=1.0,
            ),
            data_handler,
        )
        if i < 4:  # fewer than long_window (5) bars seen so far
            assert signal is None


def test_emits_long_then_exit_on_crossover():
    # Flat, then a sharp rise (short SMA crosses above long SMA -> LONG),
    # then a sharp fall back to flat (crosses back below -> EXIT).
    prices = [100.0] * 6 + [120.0] * 6 + [80.0] * 6
    store, ts = _seed_store(prices)
    data_handler = DataHandler(store)
    strategy = SMACrossoverStrategy(symbol="AAA", short_window=3, long_window=5)

    signals = []
    for i, t in enumerate(ts):
        data_handler.advance_to(t)
        signal = strategy.on_market_event(
            MarketEvent(
                timestamp=t,
                symbol="AAA",
                open=prices[i],
                high=prices[i],
                low=prices[i],
                close=prices[i],
                volume=1.0,
            ),
            data_handler,
        )
        if signal is not None:
            signals.append(signal)

    directions = [s.direction for s in signals]
    assert Direction.LONG in directions
    assert Direction.EXIT in directions
    assert directions.index(Direction.LONG) < directions.index(Direction.EXIT)
