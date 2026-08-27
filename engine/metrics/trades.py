from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class RoundTrip:
    symbol: str
    entry_ts: datetime
    exit_ts: datetime
    quantity: float  # positive magnitude of the matched lot
    entry_price: float
    exit_price: float
    realized_pnl: float  # net of allocated entry+exit costs


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def reconstruct_round_trips(trades: list) -> list[RoundTrip]:
    """FIFO lot matching per symbol, trades in chronological order (as
    Portfolio.trades naturally are). Handles partial fills and position
    flips generally — not just full open/close pairs — since sizing
    conventions vary by strategy.
    """
    open_lots: dict[str, deque] = {}
    round_trips: list[RoundTrip] = []

    for trade in trades:
        lots = open_lots.setdefault(trade.symbol, deque())
        remaining_qty = trade.quantity
        total_cost = trade.commission + trade.half_spread + trade.impact
        cost_per_share = total_cost / abs(trade.quantity) if trade.quantity else 0.0

        while remaining_qty != 0 and lots and _sign(lots[0]["quantity"]) == -_sign(remaining_qty):
            lot = lots[0]
            match_size = min(abs(lot["quantity"]), abs(remaining_qty))
            lot_direction = _sign(lot["quantity"])

            realized_gross = lot_direction * match_size * (trade.fill_price - lot["price"])
            allocated_cost = match_size * (lot["cost_per_share"] + cost_per_share)

            round_trips.append(
                RoundTrip(
                    symbol=trade.symbol,
                    entry_ts=lot["ts"],
                    exit_ts=trade.timestamp,
                    quantity=match_size,
                    entry_price=lot["price"],
                    exit_price=trade.fill_price,
                    realized_pnl=realized_gross - allocated_cost,
                )
            )

            lot["quantity"] -= lot_direction * match_size
            remaining_qty -= -lot_direction * match_size
            if lot["quantity"] == 0:
                lots.popleft()

        if remaining_qty != 0:
            lots.append(
                {
                    "ts": trade.timestamp,
                    "quantity": remaining_qty,
                    "price": trade.fill_price,
                    "cost_per_share": cost_per_share,
                }
            )

    return round_trips


def hit_rate(round_trips: list[RoundTrip]) -> float | None:
    if not round_trips:
        return None
    wins = sum(1 for rt in round_trips if rt.realized_pnl > 0)
    return wins / len(round_trips)


def avg_win(round_trips: list[RoundTrip]) -> float | None:
    wins = [rt.realized_pnl for rt in round_trips if rt.realized_pnl > 0]
    return float(np.mean(wins)) if wins else None


def avg_loss(round_trips: list[RoundTrip]) -> float | None:
    losses = [rt.realized_pnl for rt in round_trips if rt.realized_pnl < 0]
    return float(np.mean(losses)) if losses else None


def exposure(trades: list, equity_curve: list[tuple]) -> float:
    """Fraction of bars with a non-zero net position, tracked directly
    from cumulative trade quantity rather than the round-trip
    reconstruction — simpler and doesn't depend on FIFO matching being
    correct for what's fundamentally just "am I flat or not".
    """
    if not equity_curve:
        return 0.0
    trades_sorted = sorted(trades, key=lambda t: t.timestamp)
    timestamps = [t for t, _ in equity_curve]

    exposed_bars = 0
    trade_idx = 0
    position = 0.0
    for t in timestamps:
        while trade_idx < len(trades_sorted) and trades_sorted[trade_idx].timestamp <= t:
            position += trades_sorted[trade_idx].quantity
            trade_idx += 1
        if position != 0:
            exposed_bars += 1
    return exposed_bars / len(timestamps)
