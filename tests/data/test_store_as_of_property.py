from datetime import datetime

import pandas as pd
from engine.data.store import DataStore
from hypothesis import given, settings
from hypothesis import strategies as st

TS_MIN = datetime(2015, 1, 1)
TS_MAX = datetime(2025, 1, 1)

_row_strategy = st.fixed_dictionaries(
    {
        "symbol": st.sampled_from(["AAA", "BBB", "CCC"]),
        "ts": st.datetimes(min_value=TS_MIN, max_value=TS_MAX),
        "knowledge_ts": st.datetimes(min_value=TS_MIN, max_value=TS_MAX),
        "open": st.floats(min_value=1, max_value=10_000, allow_nan=False, allow_infinity=False),
        "high": st.floats(min_value=1, max_value=10_000, allow_nan=False, allow_infinity=False),
        "low": st.floats(min_value=1, max_value=10_000, allow_nan=False, allow_infinity=False),
        "close": st.floats(min_value=1, max_value=10_000, allow_nan=False, allow_infinity=False),
        "volume": st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
    }
)


@given(
    rows=st.lists(
        _row_strategy,
        min_size=1,
        max_size=30,
        unique_by=lambda r: (r["symbol"], r["ts"]),
    ),
    query_t=st.datetimes(min_value=TS_MIN, max_value=TS_MAX),
)
@settings(max_examples=100)
def test_as_of_never_returns_a_row_knowable_after_t(rows, query_t):
    """The core no-look-ahead invariant: for arbitrary stored rows and an
    arbitrary query time, as_of(t) never returns a row whose knowledge_ts
    is after t — and it returns every row that IS knowable by t.
    """
    store = DataStore(":memory:")
    df = pd.DataFrame(rows)
    df["source"] = "synthetic"
    store.insert_raw_prices(df)

    for symbol in df["symbol"].unique():
        result = store.query_as_of(symbol, query_t)

        assert (result["knowledge_ts"] <= query_t).all()

        expected_count = ((df["symbol"] == symbol) & (df["knowledge_ts"] <= query_t)).sum()
        assert len(result) == expected_count
