from datetime import datetime

import pandas as pd
from engine.data.loader import YFinanceLoader
from engine.data.store import DataStore


def _fake_history(calls):
    def fetch(symbol, start, end):
        calls.append((symbol, start, end))
        idx = pd.date_range("2020-01-01", periods=3, freq="D", name="Date")
        return pd.DataFrame(
            {
                "Open": [1.0, 2.0, 3.0],
                "High": [1.1, 2.1, 3.1],
                "Low": [0.9, 1.9, 2.9],
                "Close": [1.05, 2.05, 3.05],
                "Volume": [100, 200, 300],
                "Dividends": [0.0, 0.0, 0.5],
                "Stock Splits": [0.0, 2.0, 0.0],
            },
            index=idx,
        )

    return fetch


def test_loader_populates_raw_prices_unadjusted():
    calls = []
    store = DataStore(":memory:")
    loader = YFinanceLoader(store, fetch_fn=_fake_history(calls))

    loader.ensure_cached("TEST", datetime(2020, 1, 1), datetime(2020, 1, 4))

    prices = store.query_as_of("TEST", datetime(2020, 1, 4)).sort_values("ts")
    assert prices["close"].tolist() == [1.05, 2.05, 3.05]
    assert prices["open"].tolist() == [1.0, 2.0, 3.0]


def test_loader_populates_adjustment_factors_separately():
    calls = []
    store = DataStore(":memory:")
    loader = YFinanceLoader(store, fetch_fn=_fake_history(calls))

    loader.ensure_cached("TEST", datetime(2020, 1, 1), datetime(2020, 1, 4))

    actions = store.query_adjustment_factors("TEST")
    assert len(actions) == 2

    split_row = actions[actions["split_ratio"] != 1.0].iloc[0]
    assert split_row["split_ratio"] == 2.0

    dividend_row = actions[actions["dividend"] != 0.0].iloc[0]
    assert dividend_row["dividend"] == 0.5


def test_loader_does_not_refetch_a_cached_symbol():
    calls = []
    store = DataStore(":memory:")
    loader = YFinanceLoader(store, fetch_fn=_fake_history(calls))

    loader.ensure_cached("TEST", datetime(2020, 1, 1), datetime(2020, 1, 4))
    loader.ensure_cached("TEST", datetime(2020, 1, 1), datetime(2020, 1, 4))

    assert len(calls) == 1
