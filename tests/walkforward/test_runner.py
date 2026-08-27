import math
from itertools import product

import pytest
from engine.costs.model import ZERO_COST_MODEL
from engine.walkforward.optimizer import optimize_in_sample
from engine.walkforward.runner import run_walk_forward
from engine.walkforward.windows import WalkForwardConfig

from tests.walkforward.helpers import SYMBOL, seed_store, sma_factory

GRID = {"short_window": [3, 5], "long_window": [15, 20]}


def _oscillating_prices(n=200):
    return [100.0 + 10 * math.sin(i / 5) + 0.1 * i for i in range(n)]


def _run(n_bars=200, **config_kwargs):
    store, ts = seed_store(_oscillating_prices(n_bars))
    config = WalkForwardConfig(
        train_bars=40, test_bars=15, purge_bars=3, embargo_bars=2, **config_kwargs
    )
    result = run_walk_forward(
        store, SYMBOL, sma_factory, GRID, config, ZERO_COST_MODEL, initial_cash=100_000.0
    )
    return store, ts, config, result


def test_run_walk_forward_produces_multiple_folds():
    _, _, _, result = _run()
    assert len(result.folds) >= 2
    for fr in result.folds:
        assert fr.best_params in [dict(zip(GRID, v, strict=True)) for v in _combos()]


def _combos():
    return list(product(*GRID.values()))


def test_stitched_oos_curve_has_no_overlap_or_gap_against_the_underlying_bars():
    _, ts, _, result = _run()
    index_of = {t: i for i, t in enumerate(ts)}

    stitched_timestamps = [t for t, _ in result.stitched_equity_curve]
    fold_expected = []
    for fr in result.folds:
        fold_expected.extend(ts[index_of[fr.fold.test_start] : index_of[fr.fold.test_end] + 1])

    assert stitched_timestamps == fold_expected
    assert len(stitched_timestamps) == len(set(stitched_timestamps))


def test_stitched_curve_starts_at_initial_cash():
    _, _, _, result = _run()
    assert result.stitched_equity_curve[0][1] == 100_000.0


def test_runner_wires_fold_boundaries_into_the_optimizer_correctly():
    """The runner's fold-0 selection must match calling optimize_in_sample
    directly with that same fold's train_start/is_scored_end bounds — i.e.
    the runner isn't accidentally handing the optimizer train_end (which
    would include purge-region data) or some other boundary.
    """
    store, ts, config, result = _run()
    fold0 = result.folds[0].fold

    expected_best, expected_trials = optimize_in_sample(
        store,
        SYMBOL,
        sma_factory,
        GRID,
        fold0.train_start,
        fold0.is_scored_end,
        ZERO_COST_MODEL,
        100_000.0,
    )

    assert result.folds[0].best_params == expected_best.params
    assert result.folds[0].is_sharpe == expected_best.sharpe
    assert [t.sharpe for t in result.trials_by_fold[0]] == [t.sharpe for t in expected_trials]


def test_no_folds_raises_a_clear_error():
    store, _ = seed_store(_oscillating_prices(10))
    config = WalkForwardConfig(train_bars=40, test_bars=15, purge_bars=3, embargo_bars=2)
    with pytest.raises(ValueError):
        run_walk_forward(store, SYMBOL, sma_factory, GRID, config, ZERO_COST_MODEL)
