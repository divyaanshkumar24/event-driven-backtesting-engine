from __future__ import annotations

from engine.data.handler import DataHandler
from engine.events.event import MarketEvent, SignalEvent
from engine.strategy.base import Strategy


class RebalanceThrottle:
    """Wraps any Strategy so a signal is only forwarded once every
    `every_n_bars` bars. The wrapped strategy still evaluates every bar —
    so its own internal state (e.g. a crossover strategy's last-known
    direction) stays consistent with full information — only whether its
    output actually reaches the portfolio is gated.
    """

    def __init__(self, strategy: Strategy, every_n_bars: int):
        if every_n_bars < 1:
            raise ValueError("every_n_bars must be >= 1")
        self._strategy = strategy
        self._every_n_bars = every_n_bars
        self._bar_count = 0

    def on_market_event(self, event: MarketEvent, data: DataHandler) -> SignalEvent | None:
        signal = self._strategy.on_market_event(event, data)
        self._bar_count += 1
        if signal is None or self._bar_count % self._every_n_bars != 0:
            return None
        return signal
