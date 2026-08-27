from datetime import datetime, timedelta

import pytest
from engine.data.handler import DataHandler
from engine.events.event import Direction, MarketEvent, SignalEvent
from engine.strategy.rebalance import RebalanceThrottle


class _FixedSignalStrategy:
    """Emits a signal on every call, for isolating the throttle's own gating."""

    def __init__(self):
        self.calls = 0

    def on_market_event(self, event, data):
        self.calls += 1
        return SignalEvent(timestamp=event.timestamp, symbol=event.symbol, direction=Direction.LONG)


def _bar(i):
    return MarketEvent(
        timestamp=datetime(2020, 1, 1) + timedelta(days=i),
        symbol="AAA",
        open=100,
        high=100,
        low=100,
        close=100,
        volume=1,
    )


def test_underlying_strategy_is_called_every_bar_even_when_throttled():
    inner = _FixedSignalStrategy()
    throttled = RebalanceThrottle(inner, every_n_bars=3)
    handler = DataHandler(None)  # not used by _FixedSignalStrategy
    handler.advance_to(datetime(2020, 1, 1))

    for i in range(6):
        throttled.on_market_event(_bar(i), handler)

    assert inner.calls == 6


def test_signal_only_passes_through_every_nth_bar():
    inner = _FixedSignalStrategy()
    throttled = RebalanceThrottle(inner, every_n_bars=3)
    handler = DataHandler(None)
    handler.advance_to(datetime(2020, 1, 1))

    results = [throttled.on_market_event(_bar(i), handler) for i in range(6)]

    passed_through = [i for i, r in enumerate(results) if r is not None]
    assert passed_through == [2, 5]  # 1-indexed bar count 3 and 6 -> 0-indexed 2 and 5


def test_every_n_bars_must_be_positive():
    with pytest.raises(ValueError):
        RebalanceThrottle(_FixedSignalStrategy(), every_n_bars=0)
