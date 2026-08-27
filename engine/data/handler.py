from __future__ import annotations

from datetime import datetime

import pandas as pd

from engine.data.store import DataStore


class LookaheadError(Exception):
    """Raised when a caller asks for data at or beyond the current replay clock."""


class DataHandler:
    """The only data-access interface a strategy should ever hold.

    Wraps a DataStore with a replay clock that only the event loop advances
    (via advance_to, as bars are dispatched in strict time order). as_of(t)
    additionally refuses any request where t is beyond that clock — so
    peeking ahead isn't just filtered out, it's structurally impossible:
    the call raises instead of silently returning an empty or partial
    result that would be easy to misread as "no data yet".
    """

    def __init__(self, store: DataStore):
        self._store = store
        self._current_time: datetime | None = None

    def advance_to(self, t: datetime) -> None:
        if self._current_time is not None and t < self._current_time:
            raise ValueError(f"replay clock cannot move backward: {t} < {self._current_time}")
        self._current_time = t

    def as_of(self, t: datetime, symbol: str) -> pd.DataFrame:
        if self._current_time is None:
            raise LookaheadError("replay clock has not started; no data is available yet")
        if t > self._current_time:
            raise LookaheadError(
                f"requested t={t} is beyond the current replay clock "
                f"({self._current_time}); a strategy cannot see data before it plays"
            )
        return self._store.query_as_of(symbol, t)
