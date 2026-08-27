from __future__ import annotations

from dataclasses import dataclass

from engine.costs.model import CostModel
from engine.data.store import DataStore
from engine.portfolio.portfolio import Portfolio
from engine.walkforward.optimizer import (
    StrategyFactory,
    Trial,
    optimize_in_sample,
    run_window_backtest,
)
from engine.walkforward.windows import Fold, WalkForwardConfig, generate_folds


@dataclass(frozen=True)
class FoldResult:
    fold: Fold
    best_params: dict
    is_sharpe: float
    oos_portfolio: Portfolio


@dataclass(frozen=True)
class WalkForwardResult:
    folds: list[FoldResult]
    stitched_equity_curve: list[tuple]
    trials_by_fold: list[list[Trial]]


def stitch_oos_curves(portfolios: list[Portfolio], initial_cash: float) -> list[tuple]:
    """Chains each fold's OOS equity curve onto where the previous fold
    left off, compounding returns rather than concatenating raw levels —
    a fresh per-fold Portfolio always restarts at initial_cash, so a naive
    concatenation would produce a discontinuous, not stitched, curve.
    """
    stitched: list[tuple] = []
    running_equity = initial_cash
    for portfolio in portfolios:
        curve = portfolio.equity_curve
        if not curve:
            continue
        fold_start_equity = curve[0][1]
        for t, equity in curve:
            growth = equity / fold_start_equity if fold_start_equity else 1.0
            stitched.append((t, running_equity * growth))
        running_equity = stitched[-1][1]
    return stitched


def run_walk_forward(
    store: DataStore,
    symbol: str,
    strategy_factory: StrategyFactory,
    param_grid: dict[str, list],
    config: WalkForwardConfig,
    cost_model: CostModel,
    initial_cash: float = 100_000.0,
) -> WalkForwardResult:
    all_ts = sorted(store.query_all_raw_prices([symbol])["ts"].tolist())
    folds = generate_folds(all_ts, config)
    if not folds:
        raise ValueError(
            "no folds could be generated: not enough bars for the given "
            "train_bars/test_bars/purge_bars/embargo_bars"
        )

    fold_results: list[FoldResult] = []
    trials_by_fold: list[list[Trial]] = []

    for fold in folds:
        best_trial, trials = optimize_in_sample(
            store,
            symbol,
            strategy_factory,
            param_grid,
            fold.train_start,
            fold.is_scored_end,
            cost_model,
            initial_cash,
        )
        trials_by_fold.append(trials)

        oos_strategy = strategy_factory(best_trial.params)
        oos_portfolio = run_window_backtest(
            store, symbol, oos_strategy, fold.test_start, fold.test_end, cost_model, initial_cash
        )

        fold_results.append(
            FoldResult(
                fold=fold,
                best_params=best_trial.params,
                is_sharpe=best_trial.sharpe,
                oos_portfolio=oos_portfolio,
            )
        )

    stitched = stitch_oos_curves([fr.oos_portfolio for fr in fold_results], initial_cash)
    return WalkForwardResult(
        folds=fold_results, stitched_equity_curve=stitched, trials_by_fold=trials_by_fold
    )
