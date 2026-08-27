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


def sortino_ratio(returns: pd.Series, periods_per_year: int = 252, mar: float = 0.0) -> float:
    """Like Sharpe, but the denominator is downside deviation only —
    dispersion below `mar` (default 0), computed over the full sample
    size (periods above `mar` contribute zero, not excluded).
    """
    n = len(returns)
    if n < 2:
        return 0.0
    downside = (returns - mar).clip(upper=0.0)
    downside_std = float(((downside**2).sum() / n) ** 0.5)
    if downside_std == 0:
        return 0.0
    mean_excess = float((returns - mar).mean())
    return mean_excess / downside_std * (periods_per_year**0.5)


def max_drawdown(equity_curve: list[tuple]) -> float:
    """Most negative peak-to-trough decline, as a fraction (e.g. -0.2 for
    a 20% drawdown)."""
    if len(equity_curve) < 2:
        return 0.0
    equities = pd.Series([e for _, e in equity_curve])
    running_max = equities.cummax()
    drawdown = equities / running_max - 1.0
    return float(drawdown.min())


def max_drawdown_duration(equity_curve: list[tuple]) -> dict:
    """Longest peak-to-recovery span, in bars elapsed between the peak and
    the bar that makes a new high again. `censored` is True if the
    longest such span is still open at the end of the sample (the curve
    never made a new high again before the data ran out) — the true
    duration in that case is unknown, only a lower bound.
    """
    if len(equity_curve) < 2:
        return {"bars": 0, "censored": False}

    equities = [e for _, e in equity_curve]
    n = len(equities)
    running_max = equities[0]
    peak_idx = 0
    best_bars = 0
    best_censored = False

    for i in range(1, n):
        if equities[i] >= running_max:
            duration = i - peak_idx
            if duration > best_bars:
                best_bars = duration
                best_censored = False
            running_max = equities[i]
            peak_idx = i

    if equities[-1] < running_max:
        duration = (n - 1) - peak_idx
        if duration > best_bars:
            best_bars = duration
            best_censored = True

    return {"bars": best_bars, "censored": best_censored}


def calmar_ratio(
    returns: pd.Series, equity_curve: list[tuple], periods_per_year: int = 252
) -> float:
    cagr = annualized_return(returns, periods_per_year)
    mdd = abs(max_drawdown(equity_curve))
    if mdd == 0:
        return 0.0
    return cagr / mdd
