from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

DEFAULT_IMPACT_LOOKBACK = 20


@dataclass(frozen=True)
class CostBreakdown:
    commission: float
    half_spread: float
    impact: float

    @property
    def total(self) -> float:
        return self.commission + self.half_spread + self.impact


@dataclass(frozen=True)
class CommissionModel:
    """mode is one of "per_share", "per_trade", "bps". Only the field
    matching the active mode needs a nonzero value.
    """

    mode: str = "per_share"
    per_share: float = 0.005
    per_trade: float = 0.0
    bps: float = 0.0

    def compute(self, quantity: float, price: float) -> float:
        if self.mode == "per_share":
            return abs(quantity) * self.per_share
        if self.mode == "per_trade":
            return self.per_trade
        if self.mode == "bps":
            return abs(quantity) * price * self.bps / 10_000
        raise ValueError(f"unknown commission mode: {self.mode!r}")


@dataclass(frozen=True)
class SpreadModel:
    """Half-spread cost as a flat bps assumption on notional — there is no
    real bid/ask feed behind this yet, so it's a calibratable placeholder,
    not a modeled quote.
    """

    half_spread_bps: float = 5.0

    def compute(self, quantity: float, price: float) -> float:
        return abs(quantity) * price * self.half_spread_bps / 10_000


@dataclass(frozen=True)
class ImpactModel:
    """Square-root impact: cost_fraction = y * sigma * sqrt(|Q| / ADV)."""

    y: float = 0.1

    def compute(self, quantity: float, price: float, sigma: float, adv: float) -> float:
        if adv <= 0:
            return 0.0
        participation = abs(quantity) / adv
        impact_fraction = self.y * sigma * participation**0.5
        return impact_fraction * price * abs(quantity)


def _trailing_sigma_and_adv(history: pd.DataFrame, lookback: int) -> tuple[float, float]:
    """sigma/ADV from the trailing `lookback` bars of `history`. `history`
    must already be point-in-time filtered by the caller (i.e. it should
    stop at the order's decision time, not the fill bar) — this function
    has no way to enforce that itself.
    """
    tail = history.tail(lookback + 1)
    if tail.empty:
        return 0.0, 0.0
    adv = float(tail["volume"].mean())
    returns = tail["close"].pct_change().dropna()
    sigma = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    return sigma, adv


@dataclass(frozen=True)
class CostModel:
    commission: CommissionModel = field(default_factory=CommissionModel)
    spread: SpreadModel = field(default_factory=SpreadModel)
    impact: ImpactModel = field(default_factory=ImpactModel)
    impact_lookback: int = DEFAULT_IMPACT_LOOKBACK

    def compute(self, quantity: float, price: float, history: pd.DataFrame) -> CostBreakdown:
        sigma, adv = _trailing_sigma_and_adv(history, self.impact_lookback)
        return CostBreakdown(
            commission=self.commission.compute(quantity, price),
            half_spread=self.spread.compute(quantity, price),
            impact=self.impact.compute(quantity, price, sigma, adv),
        )


ZERO_COST_MODEL = CostModel(
    commission=CommissionModel(mode="per_share", per_share=0.0),
    spread=SpreadModel(half_spread_bps=0.0),
    impact=ImpactModel(y=0.0),
)
