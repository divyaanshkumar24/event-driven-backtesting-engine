from datetime import datetime

import pytest
from engine.costs.model import ZERO_COST_MODEL
from engine.data.handler import DataHandler
from engine.data.store import DataStore
from engine.events.event import MarketEvent, OrderEvent
from engine.execution.handler import ExecutionHandler, SameBarFillError


def _handler():
    store = DataStore(":memory:")
    data_handler = DataHandler(store)
    return ExecutionHandler(data_handler, ZERO_COST_MODEL), data_handler


def test_same_bar_fill_attempt_raises():
    """An order decided on bar T must never fill against bar T's own
    event — this is the structural guarantee behind next-bar-only fills.
    """
    execution, data_handler = _handler()
    t = datetime(2020, 1, 1)
    data_handler.advance_to(t)

    execution.submit(OrderEvent(timestamp=t, symbol="AAA", quantity=10))

    same_bar_event = MarketEvent(
        timestamp=t, symbol="AAA", open=100, high=101, low=99, close=100, volume=1000
    )
    with pytest.raises(SameBarFillError):
        execution.on_market_event(same_bar_event)


def test_next_bar_fill_uses_next_bar_open_not_close():
    execution, data_handler = _handler()
    t0 = datetime(2020, 1, 1)
    t1 = datetime(2020, 1, 2)

    data_handler.advance_to(t0)
    execution.submit(OrderEvent(timestamp=t0, symbol="AAA", quantity=10))

    data_handler.advance_to(t1)
    next_bar = MarketEvent(
        timestamp=t1, symbol="AAA", open=105.0, high=110.0, low=104.0, close=108.0, volume=1000
    )
    fills = execution.on_market_event(next_bar)

    assert len(fills) == 1
    fill = fills[0]
    assert fill.timestamp == t1
    assert fill.fill_price == 105.0  # the next bar's open, not its close
    assert fill.quantity == 10


def test_pending_order_for_a_different_symbol_is_left_untouched():
    execution, data_handler = _handler()
    t0 = datetime(2020, 1, 1)
    t1 = datetime(2020, 1, 2)

    data_handler.advance_to(t0)
    execution.submit(OrderEvent(timestamp=t0, symbol="AAA", quantity=10))

    data_handler.advance_to(t1)
    fills = execution.on_market_event(
        MarketEvent(timestamp=t1, symbol="BBB", open=10, high=11, low=9, close=10, volume=500)
    )

    assert fills == []
    assert execution._pending["AAA"][0].symbol == "AAA"
