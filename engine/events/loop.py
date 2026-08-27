from __future__ import annotations

from engine.data.handler import DataHandler
from engine.events.event import DelistingEvent, MarketEvent
from engine.events.queue import EventQueue
from engine.execution.handler import ExecutionHandler
from engine.portfolio.portfolio import Portfolio
from engine.strategy.base import Strategy


def run_backtest(
    queue: EventQueue,
    data_handler: DataHandler,
    strategy: Strategy,
    portfolio: Portfolio,
    execution_handler: ExecutionHandler,
) -> Portfolio:
    """Drains `queue` in strict time order. Within a single MarketEvent,
    any pending order for that symbol is filled BEFORE the strategy is
    given a chance to emit a new one — so an order submitted this bar is
    only ever visible to the execution handler on a later bar's event,
    never this one.
    """
    while queue:
        event = queue.pop()
        data_handler.advance_to(event.timestamp)

        if isinstance(event, MarketEvent):
            for fill in execution_handler.on_market_event(event):
                portfolio.on_fill(fill)

            portfolio.on_market_event(event)

            signal = strategy.on_market_event(event, data_handler)
            if signal is not None:
                order = portfolio.on_signal(signal)
                if order is not None:
                    execution_handler.submit(order)

        elif isinstance(event, DelistingEvent):
            fill = execution_handler.on_delisting(event, portfolio)
            if fill is not None:
                portfolio.on_fill(fill)

        else:
            raise TypeError(f"unhandled event type: {type(event)!r}")

    return portfolio
