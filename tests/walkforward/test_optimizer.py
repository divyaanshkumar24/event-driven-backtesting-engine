import math

from engine.costs.model import ZERO_COST_MODEL
from engine.walkforward.optimizer import optimize_in_sample, run_window_backtest

from tests.walkforward.helpers import SYMBOL, seed_store, sma_factory


def _oscillating_prices(n=100):
    return [100.0 + 10 * math.sin(i / 5) + 0.1 * i for i in range(n)]


def test_optimize_in_sample_returns_all_trials_and_the_best():
    store, ts = seed_store(_oscillating_prices())
    grid = {"short_window": [3, 5], "long_window": [15, 20]}

    best, trials = optimize_in_sample(
        store, SYMBOL, sma_factory, grid, ts[0], ts[-1], ZERO_COST_MODEL, initial_cash=100_000.0
    )

    assert len(trials) == 4
    assert best.sharpe == max(t.sharpe for t in trials)
    assert best.params in [t.params for t in trials]


def test_run_window_backtest_never_produces_equity_points_outside_the_window():
    store, ts = seed_store(_oscillating_prices())
    strategy = sma_factory({"short_window": 5, "long_window": 20})

    start, end = ts[10], ts[60]
    portfolio = run_window_backtest(store, SYMBOL, strategy, start, end, ZERO_COST_MODEL)

    timestamps = [t for t, _ in portfolio.equity_curve]
    assert all(start <= t <= end for t in timestamps)
    assert timestamps[0] == start
    assert timestamps[-1] == end


def test_in_sample_selection_is_blind_to_data_after_the_purge_boundary():
    """Two datasets identical through is_scored_end but sharply divergent
    afterward (i.e. within what would be the purge+embargo+test region)
    must produce IDENTICAL in-sample selection — proving nothing past the
    boundary can influence which params get chosen.
    """
    shared_head = _oscillating_prices(80)
    tail_a = [shared_head[-1] + i * 5 for i in range(1, 21)]  # sharp rally
    tail_b = [shared_head[-1] - i * 5 for i in range(1, 21)]  # sharp crash

    store_a, ts_a = seed_store(shared_head + tail_a)
    store_b, ts_b = seed_store(shared_head + tail_b)
    assert ts_a[:80] == ts_b[:80]

    is_scored_end = ts_a[79]  # last bar of the shared head
    grid = {"short_window": [3, 5], "long_window": [15, 20]}

    best_a, trials_a = optimize_in_sample(
        store_a,
        SYMBOL,
        sma_factory,
        grid,
        ts_a[0],
        is_scored_end,
        ZERO_COST_MODEL,
        initial_cash=100_000.0,
    )
    best_b, trials_b = optimize_in_sample(
        store_b,
        SYMBOL,
        sma_factory,
        grid,
        ts_b[0],
        is_scored_end,
        ZERO_COST_MODEL,
        initial_cash=100_000.0,
    )

    assert best_a.params == best_b.params
    assert best_a.sharpe == best_b.sharpe
    assert [t.sharpe for t in trials_a] == [t.sharpe for t in trials_b]
