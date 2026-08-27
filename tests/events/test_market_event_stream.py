import pandas as pd
from engine.data.store import DataStore
from engine.events.stream import build_market_event_queue, stream_market_events


def _seeded_store():
    store = DataStore(":memory:")
    ts_a = pd.date_range("2020-01-01", periods=3, freq="D")
    ts_b = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.concat(
        [
            pd.DataFrame(
                {
                    "symbol": "AAA",
                    "ts": ts_a,
                    "knowledge_ts": ts_a,
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 1.0,
                    "source": "test",
                }
            ),
            pd.DataFrame(
                {
                    "symbol": "BBB",
                    "ts": ts_b,
                    "knowledge_ts": ts_b,
                    "open": 2.0,
                    "high": 2.0,
                    "low": 2.0,
                    "close": 2.0,
                    "volume": 2.0,
                    "source": "test",
                }
            ),
        ],
        ignore_index=True,
    )
    store.insert_raw_prices(df)
    return store


def test_stream_yields_all_bars_in_knowledge_ts_order():
    events = list(stream_market_events(_seeded_store(), ["AAA", "BBB"]))

    assert len(events) == 6
    assert [e.timestamp for e in events] == sorted(e.timestamp for e in events)


def test_build_market_event_queue_pops_in_strict_time_order():
    queue = build_market_event_queue(_seeded_store(), ["AAA", "BBB"])

    popped = []
    while queue:
        popped.append(queue.pop())

    assert len(popped) == 6
    assert [e.timestamp for e in popped] == sorted(e.timestamp for e in popped)
