from datetime import datetime, timedelta

import pytest
from engine.walkforward.windows import WalkForwardConfig, generate_folds


def _timestamps(n=200):
    base = datetime(2020, 1, 1)
    return [base + timedelta(days=i) for i in range(n)]


@pytest.mark.parametrize("mode", ["rolling", "anchored"])
def test_oos_windows_are_adjacent_no_overlap_no_gap(mode):
    ts = _timestamps()
    config = WalkForwardConfig(mode=mode, train_bars=40, test_bars=15, purge_bars=3, embargo_bars=2)
    folds = generate_folds(ts, config)

    assert len(folds) >= 2, "test setup should produce multiple folds"

    index_of = {t: i for i, t in enumerate(ts)}
    for prev, nxt in zip(folds, folds[1:], strict=False):
        prev_end_idx = index_of[prev.test_end]
        next_start_idx = index_of[nxt.test_start]
        assert next_start_idx == prev_end_idx + 1


def test_purge_and_embargo_are_reflected_in_fold_boundaries():
    ts = _timestamps()
    config = WalkForwardConfig(
        mode="rolling", train_bars=40, test_bars=15, purge_bars=3, embargo_bars=2
    )
    folds = generate_folds(ts, config)
    fold = folds[0]

    index_of = {t: i for i, t in enumerate(ts)}
    assert index_of[fold.is_scored_end] == index_of[fold.train_end] - config.purge_bars
    assert index_of[fold.test_start] == index_of[fold.train_end] + 1 + config.embargo_bars
    assert index_of[fold.test_end] == index_of[fold.test_start] + config.test_bars - 1


def test_anchored_mode_grows_train_window_each_fold():
    ts = _timestamps()
    config = WalkForwardConfig(
        mode="anchored", train_bars=40, test_bars=15, purge_bars=0, embargo_bars=0
    )
    folds = generate_folds(ts, config)

    assert all(f.train_start == folds[0].train_start for f in folds)
    train_lengths = [(f.train_end - f.train_start).days for f in folds]
    assert train_lengths == sorted(train_lengths)
    assert train_lengths[-1] > train_lengths[0]


def test_rolling_mode_keeps_train_window_size_constant():
    ts = _timestamps()
    config = WalkForwardConfig(
        mode="rolling", train_bars=40, test_bars=15, purge_bars=0, embargo_bars=0
    )
    folds = generate_folds(ts, config)

    train_lengths = {(f.train_end - f.train_start).days for f in folds}
    assert train_lengths == {config.train_bars - 1}


def test_invalid_config_raises():
    with pytest.raises(ValueError):
        WalkForwardConfig(mode="bogus")
    with pytest.raises(ValueError):
        WalkForwardConfig(train_bars=0)
    with pytest.raises(ValueError):
        WalkForwardConfig(purge_bars=-1)
