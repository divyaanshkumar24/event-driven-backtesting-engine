from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from engine.data.store import DataStore
from engine.events.event import Direction, FillEvent, MarketEvent, OrderEvent, SignalEvent


@dataclass(frozen=True)
class Trade:
    timestamp: datetime
    symbol: str
    quantity: float
    fill_price: float
    commission: float
    half_spread: float
    impact: float


class Portfolio:
    """Owns cash, positions, and the equity curve. Sizing is full-equity
    target-weight: a LONG signal targets `target_weight` of current equity
    in that name, EXIT targets zero, and the order is the share delta
    needed to get there.
    """

    def __init__(
        self, store: DataStore, initial_cash: float = 100_000.0, target_weight: float = 1.0
    ):
        self._store = store
        self.cash = initial_cash
        self.target_weight = target_weight
        self.positions: dict[str, float] = {}
        self.last_price: dict[str, float] = {}
        self.trades: list[Trade] = []
        self.equity_curve: list[tuple[datetime, float]] = []

    def equity(self) -> float:
        return self.cash + sum(
            shares * self.last_price.get(symbol, 0.0) for symbol, shares in self.positions.items()
        )

    def on_market_event(self, event: MarketEvent) -> None:
        self._apply_corporate_actions(event.symbol, event.timestamp)
        self.last_price[event.symbol] = event.close
        self.equity_curve.append((event.timestamp, self.equity()))

    def _apply_corporate_actions(self, symbol: str, t) -> None:
        shares = self.positions.get(symbol, 0.0)
        if shares == 0.0:
            return
        actions = self._store.query_adjustment_factors(symbol)
        today = actions[actions["effective_date"] == t]
        for _, action in today.iterrows():
            ratio = float(action["split_ratio"])
            if ratio != 1.0:
                shares *= ratio
                self.positions[symbol] = shares
            dividend = float(action["dividend"])
            if dividend:
                self.cash += shares * dividend

    def on_signal(self, signal: SignalEvent) -> OrderEvent | None:
        price = self.last_price.get(signal.symbol)
        if price is None or price <= 0:
            return None

        target_weight = self.target_weight if signal.direction is Direction.LONG else 0.0
        target_shares = math.floor(self.equity() * target_weight / price)
        current_shares = self.positions.get(signal.symbol, 0.0)
        quantity = target_shares - current_shares
        if quantity == 0:
            return None
        return OrderEvent(timestamp=signal.timestamp, symbol=signal.symbol, quantity=quantity)

    def on_fill(self, fill: FillEvent) -> None:
        self.positions[fill.symbol] = self.positions.get(fill.symbol, 0.0) + fill.quantity
        self.cash += fill.net_cash_flow
        self.last_price[fill.symbol] = fill.fill_price
        self.trades.append(
            Trade(
                timestamp=fill.timestamp,
                symbol=fill.symbol,
                quantity=fill.quantity,
                fill_price=fill.fill_price,
                commission=fill.commission,
                half_spread=fill.half_spread,
                impact=fill.impact,
            )
        )
