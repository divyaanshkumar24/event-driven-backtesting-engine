from __future__ import annotations

from engine.data.handler import DataHandler
from engine.events.event import Direction, MarketEvent, SignalEvent


class SMACrossoverStrategy:
    """Trivial reference strategy, here only to exercise the event loop:
    LONG while the short SMA is above the long SMA, flat otherwise.
    short_window/long_window are plain public attributes so a later
    sensitivity sweep can enumerate them directly.
    """

    def __init__(self, symbol: str, short_window: int = 5, long_window: int = 20):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.symbol = symbol
        self.short_window = short_window
        self.long_window = long_window
        self._position_direction = Direction.EXIT

    def on_market_event(self, event: MarketEvent, data: DataHandler) -> SignalEvent | None:
        if event.symbol != self.symbol:
            return None

        history = data.as_of(event.timestamp, self.symbol)
        if len(history) < self.long_window:
            return None

        closes = history["close"]
        short_sma = closes.tail(self.short_window).mean()
        long_sma = closes.tail(self.long_window).mean()
        direction = Direction.LONG if short_sma > long_sma else Direction.EXIT

        if direction == self._position_direction:
            return None

        self._position_direction = direction
        return SignalEvent(timestamp=event.timestamp, symbol=event.symbol, direction=direction)
