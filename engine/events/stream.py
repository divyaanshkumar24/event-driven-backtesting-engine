from __future__ import annotations

from collections.abc import Iterable, Iterator

from engine.data.store import DataStore
from engine.events.event import MarketEvent
from engine.events.queue import EventQueue


def stream_market_events(store: DataStore, symbols: Iterable[str]) -> Iterator[MarketEvent]:
    """All cached bars for `symbols`, replayed as MarketEvents in strict
    knowledge_ts order. This reads only from the local store — no network
    calls happen here or anywhere in the event loop.
    """
    df = store.query_all_raw_prices(symbols)
    for row in df.itertuples(index=False):
        yield MarketEvent(
            timestamp=row.knowledge_ts,
            symbol=row.symbol,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
        )


def build_market_event_queue(store: DataStore, symbols: Iterable[str]) -> EventQueue:
    queue = EventQueue()
    for event in stream_market_events(store, symbols):
        queue.push(event)
    return queue
