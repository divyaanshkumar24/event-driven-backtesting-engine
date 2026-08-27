import random
from datetime import datetime, timedelta

from engine.events.event import MarketEvent
from engine.events.queue import EventQueue


def test_events_pop_in_strict_time_order_regardless_of_push_order():
    base = datetime(2020, 1, 1)
    events = [
        MarketEvent(
            timestamp=base + timedelta(days=i),
            symbol="AAA",
            open=1,
            high=1,
            low=1,
            close=1,
            volume=1,
        )
        for i in range(20)
    ]
    shuffled = events.copy()
    random.Random(42).shuffle(shuffled)

    queue = EventQueue()
    for event in shuffled:
        queue.push(event)

    popped = [queue.pop() for _ in range(len(events))]

    assert [e.timestamp for e in popped] == sorted(e.timestamp for e in events)
    assert len(queue) == 0
    assert not queue
