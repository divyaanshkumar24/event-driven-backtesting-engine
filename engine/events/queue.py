from __future__ import annotations

import heapq
from itertools import count
from typing import Any, Protocol


class _TimestampedEvent(Protocol):
    timestamp: Any


class EventQueue:
    """Time-ordered priority queue. Any event with a `.timestamp` attribute
    can be pushed; pop always returns the earliest-timestamped event, with
    insertion order as a stable tie-break.
    """

    def __init__(self):
        self._heap: list[tuple[Any, int, _TimestampedEvent]] = []
        self._counter = count()

    def push(self, event: _TimestampedEvent) -> None:
        heapq.heappush(self._heap, (event.timestamp, next(self._counter), event))

    def pop(self) -> _TimestampedEvent:
        _, _, event = heapq.heappop(self._heap)
        return event

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)
