from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True)
class MarketEvent:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class Direction(StrEnum):
    LONG = "LONG"
    EXIT = "EXIT"


@dataclass(frozen=True)
class SignalEvent:
    timestamp: datetime
    symbol: str
    direction: Direction


@dataclass(frozen=True)
class OrderEvent:
    """quantity is signed: positive to buy, negative to sell."""

    timestamp: datetime
    symbol: str
    quantity: float


@dataclass(frozen=True)
class FillEvent:
    """quantity matches the triggering order's sign. Cost breakdown is
    itemized rather than folded into fill_price, so the raw execution
    price and the cost of executing it stay separately auditable.
    """

    timestamp: datetime
    symbol: str
    quantity: float
    fill_price: float
    commission: float
    half_spread: float
    impact: float
    gross_notional: float
    net_cash_flow: float


@dataclass(frozen=True)
class DelistingEvent:
    """Marks the end of a symbol's tradeable life. Unlike a strategy order,
    this settles immediately at `price` (there is no future bar to defer
    to) rather than waiting for next-bar execution.
    """

    timestamp: datetime
    symbol: str
    price: float
