from __future__ import annotations

from engine.metrics.core import (
    annualized_return,
    calmar_ratio,
    equity_curve_returns,
    max_drawdown,
    max_drawdown_duration,
    sharpe_ratio,
    sortino_ratio,
    turnover,
)
from engine.metrics.trades import avg_loss, avg_win, exposure, hit_rate, reconstruct_round_trips


def compute_metrics(
    net_equity_curve: list[tuple],
    gross_equity_curve: list[tuple],
    trades: list,
    deflated_sharpe: dict,
    periods_per_year: int = 252,
) -> dict:
    """The full metric set for one bundle. deflated_sharpe is passed in
    rather than recomputed here — it's the same computation the bias
    auditor already does (pooled trial Sharpes across walk-forward
    folds), and duplicating it risks two slightly different DSR numbers
    landing in the same bundle.
    """
    net_returns = equity_curve_returns(net_equity_curve)
    gross_returns = equity_curve_returns(gross_equity_curve)
    round_trips = reconstruct_round_trips(trades)

    return {
        "cagr": annualized_return(net_returns, periods_per_year),
        "sharpe": sharpe_ratio(net_returns, periods_per_year),
        "sortino": sortino_ratio(net_returns, periods_per_year),
        "calmar": calmar_ratio(net_returns, net_equity_curve, periods_per_year),
        "max_drawdown": max_drawdown(net_equity_curve),
        "max_drawdown_duration": max_drawdown_duration(net_equity_curve),
        "hit_rate": hit_rate(round_trips),
        "avg_win": avg_win(round_trips),
        "avg_loss": avg_loss(round_trips),
        "exposure": exposure(trades, net_equity_curve),
        "turnover": turnover(trades, net_equity_curve),
        "deflated_sharpe": deflated_sharpe,
        "gross_vs_net": {
            "gross_cagr": annualized_return(gross_returns, periods_per_year),
            "net_cagr": annualized_return(net_returns, periods_per_year),
            "gross_sharpe": sharpe_ratio(gross_returns, periods_per_year),
            "net_sharpe": sharpe_ratio(net_returns, periods_per_year),
        },
    }
