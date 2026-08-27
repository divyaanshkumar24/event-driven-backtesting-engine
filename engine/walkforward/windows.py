from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Fold:
    train_start: datetime
    train_end: datetime  # nominal end of the training window, before purge trimming
    is_scored_end: datetime  # last bar actually used for in-sample scoring (train_end - purge_bars)
    test_start: datetime  # train_end + embargo_bars
    test_end: datetime


@dataclass(frozen=True)
class WalkForwardConfig:
    """Consecutive test windows advance by exactly `test_bars` each fold —
    there is no independent step size — so OOS segments are adjacent by
    construction: no gap, no overlap, regardless of mode.
    """

    mode: Literal["rolling", "anchored"] = "rolling"
    train_bars: int = 60
    test_bars: int = 20
    purge_bars: int = 5
    embargo_bars: int = 5

    def __post_init__(self):
        if self.mode not in ("rolling", "anchored"):
            raise ValueError(f"mode must be 'rolling' or 'anchored', got {self.mode!r}")
        if self.train_bars <= 0 or self.test_bars <= 0:
            raise ValueError("train_bars and test_bars must be positive")
        if self.purge_bars < 0 or self.embargo_bars < 0:
            raise ValueError("purge_bars and embargo_bars must be non-negative")


def generate_folds(timestamps: list[datetime], config: WalkForwardConfig) -> list[Fold]:
    """timestamps must be sorted ascending, one entry per available bar for
    the traded symbol. The in-sample event stream for fold k is restricted
    to [train_start, is_scored_end] and the OOS stream to [test_start,
    test_end] — purge and embargo are enforced by the caller never handing
    the excluded bars to a backtest run at all, not by filtering results
    after the fact.
    """
    n = len(timestamps)
    folds: list[Fold] = []
    k = 0
    while True:
        if config.mode == "anchored":
            train_start_idx = 0
            train_end_idx = config.train_bars - 1 + k * config.test_bars
        else:
            train_start_idx = k * config.test_bars
            train_end_idx = train_start_idx + config.train_bars - 1

        is_scored_end_idx = train_end_idx - config.purge_bars
        test_start_idx = train_end_idx + 1 + config.embargo_bars
        test_end_idx = test_start_idx + config.test_bars - 1

        if test_end_idx >= n or is_scored_end_idx < train_start_idx:
            break

        folds.append(
            Fold(
                train_start=timestamps[train_start_idx],
                train_end=timestamps[train_end_idx],
                is_scored_end=timestamps[is_scored_end_idx],
                test_start=timestamps[test_start_idx],
                test_end=timestamps[test_end_idx],
            )
        )
        k += 1

    return folds
