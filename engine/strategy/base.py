from __future__ import annotations

from typing import Protocol

from engine.data.handler import DataHandler
from engine.events.event import MarketEvent, SignalEvent


class Strategy(Protocol):
    def on_market_event(self, event: MarketEvent, data: DataHandler) -> SignalEvent | None: ...
