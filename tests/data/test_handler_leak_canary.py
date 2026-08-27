from datetime import datetime

import pandas as pd
import pytest
from engine.data.handler import DataHandler, LookaheadError
from engine.data.store import DataStore


def _store_with_five_days():
    store = DataStore(":memory:")
    ts = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "symbol": "AAA",
            "ts": ts,
            "knowledge_ts": ts,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 100.0,
            "source": "test",
        }
    )
    store.insert_raw_prices(df)
    return store


def test_as_of_before_clock_starts_raises():
    handler = DataHandler(_store_with_five_days())
    with pytest.raises(LookaheadError):
        handler.as_of(datetime(2020, 1, 1), "AAA")


def test_strategy_cannot_peek_ahead_of_replay_clock():
    """A strategy that only ever sees `handler` cannot construct a query
    that returns data the event loop hasn't dispatched yet — the call
    raises rather than silently returning an empty or truncated frame.
    """
    handler = DataHandler(_store_with_five_days())
    handler.advance_to(datetime(2020, 1, 2))

    def strategy_tries_to_peek(h, t):
        return h.as_of(t, "AAA")

    with pytest.raises(LookaheadError):
        strategy_tries_to_peek(handler, datetime(2020, 1, 5))


def test_as_of_at_or_before_clock_succeeds_and_is_bounded():
    handler = DataHandler(_store_with_five_days())
    handler.advance_to(datetime(2020, 1, 3))

    result = handler.as_of(datetime(2020, 1, 3), "AAA")

    assert len(result) == 3
    assert (result["knowledge_ts"] <= datetime(2020, 1, 3)).all()


def test_clock_cannot_move_backward():
    handler = DataHandler(_store_with_five_days())
    handler.advance_to(datetime(2020, 1, 3))
    with pytest.raises(ValueError):
        handler.advance_to(datetime(2020, 1, 2))
