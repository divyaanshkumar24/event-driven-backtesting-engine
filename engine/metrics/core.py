from __future__ import annotations

import pandas as pd


def equity_curve_returns(equity_curve: list[tuple]) -> pd.Series:
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)
    equities = pd.Series([e for _, e in equity_curve])
    return equities.pct_change().dropna()


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * (periods_per_year**0.5))


def annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    n = len(returns)
    if n == 0:
        return 0.0
    compounded = float((1 + returns).prod())
    if compounded <= 0:
        return -1.0
    return compounded ** (periods_per_year / n) - 1


def turnover(trades: list, equity_curve: list[tuple]) -> float:
    """Total traded notional as a multiple of average equity over the
    period — e.g. 3.0 means the strategy traded three times its average
    equity in notional terms.
    """
    if not equity_curve:
        return 0.0
    avg_equity = sum(e for _, e in equity_curve) / len(equity_curve)
    if avg_equity <= 0:
        return 0.0
    traded_notional = sum(abs(t.quantity * t.fill_price) for t in trades)
    return traded_notional / avg_equity
