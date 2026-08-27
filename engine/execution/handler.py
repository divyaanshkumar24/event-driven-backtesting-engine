from __future__ import annotations

from engine.costs.model import CostBreakdown, CostModel
from engine.data.handler import DataHandler
from engine.events.event import DelistingEvent, FillEvent, MarketEvent, OrderEvent
from engine.portfolio.portfolio import Portfolio


class SameBarFillError(Exception):
    """Raised when an order would fill on the same bar (or earlier) than
    the one that produced it. Fills only ever happen on a strictly later
    bar than the order's decision time — this is enforced here, not just
    by how the event loop happens to call things.
    """


def _build_fill(
    order: OrderEvent, fill_price: float, timestamp, breakdown: CostBreakdown
) -> FillEvent:
    notional = order.quantity * fill_price
    return FillEvent(
        timestamp=timestamp,
        symbol=order.symbol,
        quantity=order.quantity,
        fill_price=fill_price,
        commission=breakdown.commission,
        half_spread=breakdown.half_spread,
        impact=breakdown.impact,
        gross_notional=abs(notional),
        net_cash_flow=-notional - breakdown.total,
    )


class ExecutionHandler:
    """Fills orders on the open of the next bar for that symbol — never
    the bar that produced them. Cost sizing (impact's sigma/ADV) is drawn
    from data as of the order's own decision time, not the fill bar, so a
    trade's own volume can't leak into what it costs to place it.
    """

    def __init__(self, data_handler: DataHandler, cost_model: CostModel):
        self._data = data_handler
        self._cost_model = cost_model
        self._pending: dict[str, list[OrderEvent]] = {}

    def submit(self, order: OrderEvent) -> None:
        self._pending.setdefault(order.symbol, []).append(order)

    def on_market_event(self, event: MarketEvent) -> list[FillEvent]:
        orders = self._pending.pop(event.symbol, [])
        fills = []
        for order in orders:
            if order.timestamp >= event.timestamp:
                raise SameBarFillError(
                    f"order for {order.symbol} decided at {order.timestamp} cannot fill "
                    f"on bar {event.timestamp}; a fill must happen on a strictly later bar"
                )
            history = self._data.as_of(order.timestamp, order.symbol)
            breakdown = self._cost_model.compute(order.quantity, event.open, history)
            fills.append(_build_fill(order, event.open, event.timestamp, breakdown))
        return fills

    def on_delisting(self, event: DelistingEvent, portfolio: Portfolio) -> FillEvent | None:
        shares = portfolio.positions.get(event.symbol, 0.0)
        if shares == 0.0:
            return None
        order = OrderEvent(timestamp=event.timestamp, symbol=event.symbol, quantity=-shares)
        history = self._data.as_of(event.timestamp, event.symbol)
        breakdown = self._cost_model.compute(order.quantity, event.price, history)
        return _build_fill(order, event.price, event.timestamp, breakdown)
