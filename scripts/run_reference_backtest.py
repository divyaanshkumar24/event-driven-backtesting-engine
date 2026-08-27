"""Runs the SMA-crossover reference strategy end-to-end on real data and
writes a real report bundle to bundles/run_<id>/.

    .venv/bin/python scripts/run_reference_backtest.py

Fetches (and locally caches) SPY daily bars via yfinance, walk-forward
optimizes short_window/long_window, audits the result for bias, computes
the full metric set and sensitivity panels, and writes the bundle.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

from engine.audit.bias_audit import build_bias_audit
from engine.bundle.viewer_export import export_bundle_for_viewer
from engine.bundle.writer import generate_run_id, hash_price_data, write_bundle
from engine.costs.model import ZERO_COST_MODEL, CommissionModel, CostModel, ImpactModel, SpreadModel
from engine.data.loader import YFinanceLoader
from engine.data.store import DataStore
from engine.metrics.report import compute_metrics
from engine.strategy.sma_crossover import SMACrossoverStrategy
from engine.walkforward.runner import rerun_oos_with_cost_model, run_walk_forward
from engine.walkforward.sensitivity import param_sensitivity, rebalance_frequency_sensitivity
from engine.walkforward.windows import WalkForwardConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
SYMBOL = "SPY"
FETCH_START = datetime(2023, 1, 1)
INITIAL_CASH = 100_000.0

PARAM_GRID = {"short_window": [5, 10, 20], "long_window": [50, 100, 150]}
WALKFORWARD_CONFIG = WalkForwardConfig(
    mode="rolling", train_bars=252, test_bars=126, purge_bars=10, embargo_bars=5
)
COST_MODEL = CostModel(
    commission=CommissionModel(mode="per_share", per_share=0.005),
    spread=SpreadModel(half_spread_bps=5.0),
    impact=ImpactModel(y=0.1),
)
REBALANCE_FREQUENCIES = [1, 3, 5, 10, 21]


def strategy_factory(params: dict) -> SMACrossoverStrategy:
    return SMACrossoverStrategy(symbol=SYMBOL, **params)


def main() -> Path:
    store = DataStore(REPO_ROOT / "data_cache" / "market_data.duckdb")
    loader = YFinanceLoader(store)
    loader.ensure_cached(SYMBOL, FETCH_START, datetime.now(UTC))

    result = run_walk_forward(
        store, SYMBOL, strategy_factory, PARAM_GRID, WALKFORWARD_CONFIG, COST_MODEL, INITIAL_CASH
    )

    print(f"Walk-forward produced {len(result.folds)} folds.")
    for fr in result.folds:
        print(
            f"  fold test {fr.fold.test_start.date()}..{fr.fold.test_end.date()}: "
            f"params={fr.best_params} is_sharpe={fr.is_sharpe:.3f}"
        )

    bias_audit = build_bias_audit(store, SYMBOL, strategy_factory, result, COST_MODEL, INITIAL_CASH)

    gross_curve = rerun_oos_with_cost_model(
        store, SYMBOL, strategy_factory, result, ZERO_COST_MODEL, INITIAL_CASH
    )
    trades = [t for fr in result.folds for t in fr.oos_portfolio.trades]
    metrics = compute_metrics(
        result.stitched_equity_curve,
        gross_curve,
        trades,
        bias_audit["overfitting_analysis"]["value"]["deflated_sharpe"],
    )

    all_ts = store.query_all_raw_prices([SYMBOL])["ts"]
    full_start, full_end = all_ts.min(), all_ts.max()
    reference_params = result.folds[-1].best_params  # most recent fold's selection

    sensitivity = {
        "param_grid": param_sensitivity(
            store,
            SYMBOL,
            strategy_factory,
            PARAM_GRID,
            full_start,
            full_end,
            COST_MODEL,
            INITIAL_CASH,
        ),
        "rebalance_frequency": rebalance_frequency_sensitivity(
            store,
            SYMBOL,
            strategy_factory,
            reference_params,
            REBALANCE_FREQUENCIES,
            full_start,
            full_end,
            COST_MODEL,
            INITIAL_CASH,
        ),
        "reference_params_used_for_rebalance_sweep": reference_params,
    }

    data_hash = hash_price_data(store, SYMBOL)
    manifest_inputs = {
        "symbol": SYMBOL,
        "fetch_start": FETCH_START.isoformat(),
        "data_range": {"start": str(full_start), "end": str(full_end)},
        "strategy": "SMACrossoverStrategy",
        "param_grid": PARAM_GRID,
        "walkforward_config": dataclasses.asdict(WALKFORWARD_CONFIG),
        "cost_model": dataclasses.asdict(COST_MODEL),
        "initial_cash": INITIAL_CASH,
    }
    run_id = generate_run_id(manifest_inputs, data_hash)

    bundle_dir = write_bundle(
        REPO_ROOT / "bundles",
        run_id,
        manifest_inputs=manifest_inputs,
        metrics=metrics,
        equity_curve=result.stitched_equity_curve,
        trades=trades,
        sensitivity=sensitivity,
        bias_audit=bias_audit,
        data_hash=data_hash,
    )

    print(f"\nBundle written to {bundle_dir}")

    viewer_data_dir = export_bundle_for_viewer(
        bundle_dir,
        store,
        SYMBOL,
        result.stitched_equity_curve,
        gross_curve,
        INITIAL_CASH,
        REPO_ROOT / "viewer" / "public" / "data" / "current",
    )
    print(f"Viewer data written to {viewer_data_dir}")

    return bundle_dir


if __name__ == "__main__":
    main()
