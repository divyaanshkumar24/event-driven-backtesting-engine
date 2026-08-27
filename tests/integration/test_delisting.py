from datetime import datetime, timedelta

import pandas as pd
from engine.costs.model import ZERO_COST_MODEL
from engine.data.handler import DataHandler
from engine.data.store import DataStore
from engine.events.event import DelistingEvent
from engine.events.loop import run_backtest
from engine.events.queue import EventQueue
from engine.events.stream import stream_market_events
from engine.execution.handler import ExecutionHandler
from engine.portfolio.portfolio import Portfolio


class _NoOpStrategy:
    """Never signals, so the delisting event is the only thing that can
    force a fill in this test.
    """

    def on_market_event(self, event, data):
        return None


def test_delisting_force_liquidates_and_records_a_trade():
    store = DataStore(":memory:")
    base = datetime(2020, 1, 1)
    prices = [100.0, 101.0, 99.0]
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

    data_handler = DataHandler(store)
    execution = ExecutionHandler(data_handler, ZERO_COST_MODEL)
    portfolio = Portfolio(store, initial_cash=10_000.0)
    portfolio.positions["AAA"] = 20.0
    portfolio.last_price["AAA"] = 99.0

    queue = EventQueue()
    for event in stream_market_events(store, ["AAA"]):
        queue.push(event)
    delisting_ts = ts[-1] + timedelta(days=1)
    queue.push(DelistingEvent(timestamp=delisting_ts, symbol="AAA", price=40.0))

    run_backtest(queue, data_handler, _NoOpStrategy(), portfolio, execution)

    assert portfolio.positions["AAA"] == 0.0
    assert len(portfolio.trades) == 1

    trade = portfolio.trades[0]
    assert trade.quantity == -20.0
    assert trade.fill_price == 40.0
    assert portfolio.cash == 10_000.0 + 20.0 * 40.0


def test_delisting_of_a_flat_position_is_a_no_op():
    store = DataStore(":memory:")
    data_handler = DataHandler(store)
    execution = ExecutionHandler(data_handler, ZERO_COST_MODEL)
    portfolio = Portfolio(store, initial_cash=10_000.0)

    queue = EventQueue()
    queue.push(DelistingEvent(timestamp=datetime(2020, 1, 1), symbol="AAA", price=40.0))

    run_backtest(queue, data_handler, _NoOpStrategy(), portfolio, execution)

    assert portfolio.trades == []
    assert portfolio.cash == 10_000.0
