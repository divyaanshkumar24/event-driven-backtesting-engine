from datetime import datetime

import pandas as pd
from engine.data.store import DataStore
from engine.events.event import Direction, FillEvent, MarketEvent, SignalEvent
from engine.portfolio.portfolio import Portfolio


def test_on_signal_long_sizes_to_full_equity_target_weight():
    store = DataStore(":memory:")
    portfolio = Portfolio(store, initial_cash=10_000.0, target_weight=1.0)
    portfolio.last_price["AAA"] = 100.0

    order = portfolio.on_signal(SignalEvent(datetime(2020, 1, 1), "AAA", Direction.LONG))

    assert order is not None
    assert order.quantity == 100  # floor(10_000 / 100)


def test_on_signal_exit_targets_zero():
    store = DataStore(":memory:")
    portfolio = Portfolio(store, initial_cash=10_000.0, target_weight=1.0)
    portfolio.last_price["AAA"] = 100.0
    portfolio.positions["AAA"] = 50.0

    order = portfolio.on_signal(SignalEvent(datetime(2020, 1, 1), "AAA", Direction.EXIT))

    assert order is not None
    assert order.quantity == -50


def test_on_fill_updates_cash_and_position():
    store = DataStore(":memory:")
    portfolio = Portfolio(store, initial_cash=10_000.0)
    fill = FillEvent(
        timestamp=datetime(2020, 1, 2),
        symbol="AAA",
        quantity=10,
        fill_price=100.0,
        commission=1.0,
        half_spread=0.5,
        impact=0.0,
        gross_notional=1000.0,
        net_cash_flow=-1001.5,
    )

    portfolio.on_fill(fill)

    assert portfolio.positions["AAA"] == 10
    assert portfolio.cash == 10_000.0 - 1001.5
    assert len(portfolio.trades) == 1


def test_known_split_keeps_position_value_continuous():
    """A 2:1 split, with no genuine price movement on the split day, must
    leave equity unchanged: shares double, price halves.
    """
    store = DataStore(":memory:")
    split_date = datetime(2020, 2, 1)
    store.insert_adjustment_factors(
        pd.DataFrame(
            {
                "symbol": ["AAA"],
                "effective_date": [split_date],
                "knowledge_ts": [split_date],
                "split_ratio": [2.0],
                "dividend": [0.0],
                "source": ["test"],
            }
        )
    )

    portfolio = Portfolio(store, initial_cash=5_000.0)
    portfolio.positions["AAA"] = 10.0
    portfolio.last_price["AAA"] = 100.0
    equity_before = portfolio.equity()

    portfolio.on_market_event(
        MarketEvent(
            timestamp=split_date,
            symbol="AAA",
            open=50.0,
            high=51.0,
            low=49.0,
            close=50.0,
            volume=1_000_000.0,
        )
    )

    assert portfolio.positions["AAA"] == 20.0
    assert portfolio.last_price["AAA"] == 50.0
    assert portfolio.equity() == equity_before


def test_dividend_credits_cash_without_changing_shares():
    store = DataStore(":memory:")
    ex_date = datetime(2020, 3, 1)
    store.insert_adjustment_factors(
        pd.DataFrame(
            {
                "symbol": ["AAA"],
                "effective_date": [ex_date],
                "knowledge_ts": [ex_date],
                "split_ratio": [1.0],
                "dividend": [0.5],
                "source": ["test"],
            }
        )
    )

    portfolio = Portfolio(store, initial_cash=1_000.0)
    portfolio.positions["AAA"] = 10.0
    portfolio.last_price["AAA"] = 100.0

    portfolio.on_market_event(
        MarketEvent(
            timestamp=ex_date,
            symbol="AAA",
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=1_000_000.0,
        )
    )

    assert portfolio.positions["AAA"] == 10.0
    assert portfolio.cash == 1_000.0 + 10.0 * 0.5
