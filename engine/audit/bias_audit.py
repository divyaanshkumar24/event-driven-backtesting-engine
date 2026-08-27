from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine.audit.stats import deflated_sharpe_ratio, pbo_cscv
from engine.costs.model import ZERO_COST_MODEL, CommissionModel, CostModel, ImpactModel, SpreadModel
from engine.data.store import DataStore
from engine.metrics.core import annualized_return, equity_curve_returns, sharpe_ratio, turnover
from engine.walkforward.optimizer import StrategyFactory, run_window_backtest
from engine.walkforward.runner import WalkForwardResult, stitch_oos_curves


def _field(status: str, value, explanation: str) -> dict:
    return {"status": status, "value": value, "explanation": explanation}


def _scale_cost_model(base: CostModel, multiple: float) -> CostModel:
    return CostModel(
        commission=CommissionModel(
            mode=base.commission.mode,
            per_share=base.commission.per_share * multiple,
            per_trade=base.commission.per_trade * multiple,
            bps=base.commission.bps * multiple,
        ),
        spread=SpreadModel(half_spread_bps=base.spread.half_spread_bps * multiple),
        impact=ImpactModel(y=base.impact.y * multiple),
        impact_lookback=base.impact_lookback,
    )


def _net_annualized_return(
    store: DataStore,
    symbol: str,
    strategy_factory: StrategyFactory,
    result: WalkForwardResult,
    cost_model: CostModel,
    initial_cash: float,
) -> float:
    portfolios = [
        run_window_backtest(
            store,
            symbol,
            strategy_factory(fr.best_params),
            fr.fold.test_start,
            fr.fold.test_end,
            cost_model,
            initial_cash,
        )
        for fr in result.folds
    ]
    curve = stitch_oos_curves(portfolios, initial_cash)
    return annualized_return(equity_curve_returns(curve))


def _find_zero_crossing_multiple(
    f, low: float = 1.0, max_high: float = 1024.0, iterations: int = 12
) -> float | None:
    """Smallest multiple >= low where f(multiple) <= 0, via geometric
    bracketing then bisection. None if f stays positive out to max_high.
    """
    if f(low) <= 0:
        return low
    high = low * 2
    while f(high) > 0:
        high *= 2
        if high > max_high:
            return None
    lo, hi = low, high
    for _ in range(iterations):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return hi


def _cost_analysis(store, symbol, strategy_factory, result, cost_model, initial_cash) -> dict:
    gross_portfolios = [
        run_window_backtest(
            store,
            symbol,
            strategy_factory(fr.best_params),
            fr.fold.test_start,
            fr.fold.test_end,
            ZERO_COST_MODEL,
            initial_cash,
        )
        for fr in result.folds
    ]
    gross_curve = stitch_oos_curves(gross_portfolios, initial_cash)
    gross_returns = equity_curve_returns(gross_curve)
    net_returns = equity_curve_returns(result.stitched_equity_curve)

    gross_sharpe = sharpe_ratio(gross_returns)
    net_sharpe = sharpe_ratio(net_returns)
    cost_drag = annualized_return(gross_returns) - annualized_return(net_returns)

    breakeven_multiple = _find_zero_crossing_multiple(
        lambda m: _net_annualized_return(
            store, symbol, strategy_factory, result, _scale_cost_model(cost_model, m), initial_cash
        )
    )

    value = {
        "gross_sharpe": gross_sharpe,
        "net_sharpe": net_sharpe,
        "annualized_cost_drag": cost_drag,
        "breakeven_cost_multiple": breakeven_multiple,
    }
    status = "pass" if net_sharpe <= gross_sharpe else "warn"
    explanation = (
        "gross_sharpe/net_sharpe use the same OOS windows and chosen params, differing only in "
        "cost model (zero-cost vs the supplied CostModel). breakeven_cost_multiple is the smallest "
        "multiplier on all cost components (commission, spread, impact) at which annualized net "
        "return crosses zero; null means it stayed positive up to a 1024x cost multiple."
    )
    return _field(status, value, explanation)


def _turnover_field(result: WalkForwardResult) -> dict:
    trades = [t for fr in result.folds for t in fr.oos_portfolio.trades]
    value = turnover(trades, result.stitched_equity_curve)
    return _field(
        "pass",
        value,
        "Total traded notional across all OOS fold trades, as a multiple of average OOS equity.",
    )


def _survivorship_field(had_delistings: bool) -> dict:
    if had_delistings:
        return _field(
            "flagged",
            "delistings-present",
            "DelistingEvents occurred during this run; a with/without-delisted Sharpe delta was "
            "not computed in this phase — only the flag is reported.",
        )
    return _field(
        "flagged",
        "survivorship-limited",
        "No point-in-time delisted-universe feed is wired up yet (the data source is yfinance, "
        "which only serves currently-listed history). Per the fixed spec, an explicit "
        "survivorship-limited flag is reported instead of a with/without-delisted Sharpe delta.",
    )


def _overfitting_field(result: WalkForwardResult) -> dict:
    all_trial_sharpes = [t.sharpe for trials in result.trials_by_fold for t in trials]
    n_combos = len(result.trials_by_fold[0]) if result.trials_by_fold else 0

    dsr = deflated_sharpe_ratio(
        equity_curve_returns(result.stitched_equity_curve), all_trial_sharpes
    )

    pbo = None
    last_fold_trials = result.trials_by_fold[-1] if result.trials_by_fold else []
    if len(last_fold_trials) >= 2:
        columns = [
            equity_curve_returns(t.portfolio.equity_curve).to_numpy() for t in last_fold_trials
        ]
        min_len = min(len(c) for c in columns)
        if min_len >= 16:  # need enough bars for at least a couple of observations per CSCV block
            n_splits = min(8, min_len // 2)
            n_splits -= n_splits % 2
            matrix = np.column_stack([c[-min_len:] for c in columns])
            pbo = pbo_cscv(matrix, n_splits=max(n_splits, 2))

    value = {
        "n_param_combos_tested_per_fold": n_combos,
        "n_folds": len(result.folds),
        "deflated_sharpe": dsr,
        "pbo": pbo,
    }
    status = "warn" if dsr["dsr"] < 0.95 or (pbo and pbo["pbo"] > 0.5) else "pass"
    explanation = (
        "deflated_sharpe corrects the stitched OOS Sharpe for having tried "
        f"{len(all_trial_sharpes)} param combinations pooled across all folds (a conservative "
        "count of the full multiple-testing exposure). pbo is computed via CSCV on the last "
        "fold's per-combo in-sample return matrix; null if there weren't enough combos/bars."
    )
    return _field(status, value, explanation)


def _is_oos_degradation_field(result: WalkForwardResult) -> dict:
    is_sharpes = [fr.is_sharpe for fr in result.folds]
    is_avg = float(np.mean(is_sharpes)) if is_sharpes else 0.0
    oos_sharpe = sharpe_ratio(equity_curve_returns(result.stitched_equity_curve))
    value = {"is_sharpe_avg": is_avg, "oos_sharpe": oos_sharpe, "degradation": is_avg - oos_sharpe}
    status = "warn" if is_avg > 0 and oos_sharpe < is_avg * 0.5 else "pass"
    return _field(
        status,
        value,
        "is_sharpe_avg is the mean per-fold in-sample Sharpe of the selected params; oos_sharpe is "
        "the stitched out-of-sample Sharpe. A large positive degradation suggests the in-sample "
        "selection process found noise rather than a robust edge.",
    )


def _regime_breakdown_field(store: DataStore, symbol: str, result: WalkForwardResult) -> dict:
    prices = store.query_all_raw_prices([symbol]).sort_values("ts")
    price_series = prices.set_index("ts")["close"]
    trailing_vol = price_series.pct_change().rolling(20).std()

    if len(result.stitched_equity_curve) < 4:
        return _field("not_applicable", None, "Not enough OOS observations to bucket into regimes.")

    oos_df = pd.DataFrame(result.stitched_equity_curve, columns=["ts", "equity"]).set_index("ts")
    oos_df["return"] = oos_df["equity"].pct_change()
    oos_df["trailing_vol"] = trailing_vol.reindex(oos_df.index)
    oos_df = oos_df.dropna(subset=["return", "trailing_vol"])

    if len(oos_df) < 6:
        return _field(
            "not_applicable",
            None,
            "Not enough overlapping OOS/volatility observations for tercile buckets.",
        )

    oos_df["regime"] = pd.qcut(
        oos_df["trailing_vol"], 3, labels=["low_vol", "mid_vol", "high_vol"], duplicates="drop"
    )
    breakdown = {
        str(regime): (sharpe_ratio(group["return"]) if len(group) > 1 else None)
        for regime, group in oos_df.groupby("regime", observed=True)
    }
    return _field(
        "pass",
        breakdown,
        "Per-regime OOS Sharpe, with regimes defined as terciles of the underlying's trailing "
        "20-bar realized volatility over the stitched OOS period.",
    )


def _capacity_field(store, symbol, strategy_factory, result, cost_model, initial_cash) -> dict:
    multiple = _find_zero_crossing_multiple(
        lambda m: _net_annualized_return(
            store, symbol, strategy_factory, result, cost_model, initial_cash * m
        )
    )
    capacity_aum = initial_cash * multiple if multiple is not None else None
    status = "pass" if capacity_aum is not None else "not_applicable"
    return _field(
        status,
        capacity_aum,
        "AUM (scaling initial_cash, holding target_weight fixed) at which the strategy's own "
        "square-root market impact drives annualized net OOS return to zero. Null means capacity "
        "wasn't reached within a 1024x AUM scale.",
    )


def build_bias_audit(
    store: DataStore,
    symbol: str,
    strategy_factory: StrategyFactory,
    result: WalkForwardResult,
    cost_model: CostModel,
    initial_cash: float = 100_000.0,
    had_delistings: bool = False,
) -> dict:
    return {
        "look_ahead_violations": _field(
            "pass",
            0,
            "Not a post-hoc scan: DataHandler.as_of()/LookaheadError and the execution handler's "
            "SameBarFillError make a look-ahead or same-bar fill raise and abort the run rather "
            "than appear silently in output, so a completed run implies zero violations.",
        ),
        "fill_timing_assumption": _field(
            "pass",
            "next-bar-open",
            "Decisions use data as of the close of bar t; orders fill at the open of the next bar "
            "for that symbol. Same-bar fills are structurally rejected.",
        ),
        "survivorship_posture": _survivorship_field(had_delistings),
        "cost_analysis": _cost_analysis(
            store, symbol, strategy_factory, result, cost_model, initial_cash
        ),
        "turnover": _turnover_field(result),
        "overfitting_analysis": _overfitting_field(result),
        "is_oos_degradation": _is_oos_degradation_field(result),
        "regime_breakdown": _regime_breakdown_field(store, symbol, result),
        "capacity": _capacity_field(
            store, symbol, strategy_factory, result, cost_model, initial_cash
        ),
    }


def write_bias_audit(path: str | Path, audit: dict) -> None:
    Path(path).write_text(json.dumps(audit, indent=2, default=str))
