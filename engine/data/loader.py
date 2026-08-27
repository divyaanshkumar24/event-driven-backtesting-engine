from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pandas as pd
import yfinance as yf

from engine.data.store import DataStore

SOURCE = "yfinance"

FetchFn = Callable[[str, datetime, datetime], pd.DataFrame]


def _default_fetch(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    # auto_adjust=False + actions=True: raw OHLCV plus the Dividends and
    # Stock Splits columns needed to populate adjustment_factors. Never
    # request the back-adjusted series — that would collapse the two
    # tables this store is built to keep separate.
    return yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False, actions=True)


class YFinanceLoader:
    """Fetches raw prices + corporate actions and caches them to the local
    DataStore. A symbol already present for this source is never re-fetched
    — the cache is treated as immutable once written.
    """

    def __init__(self, store: DataStore, fetch_fn: FetchFn = _default_fetch):
        self._store = store
        self._fetch_fn = fetch_fn

    def ensure_cached(self, symbol: str, start: datetime, end: datetime) -> None:
        if self._store.has_symbol(symbol, SOURCE):
            return
        raw = self._fetch_fn(symbol, start, end)
        prices, actions = _normalize(symbol, raw)
        self._store.insert_raw_prices(prices)
        self._store.insert_adjustment_factors(actions)


def _normalize(symbol: str, raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = raw.reset_index()
    ts_col = "Date" if "Date" in raw.columns else "Datetime"
    ts = pd.to_datetime(raw[ts_col]).dt.tz_localize(None)

    prices = pd.DataFrame(
        {
            "symbol": symbol,
            "ts": ts,
            "knowledge_ts": ts,
            "open": raw["Open"].astype(float),
            "high": raw["High"].astype(float),
            "low": raw["Low"].astype(float),
            "close": raw["Close"].astype(float),
            "volume": raw["Volume"].astype(float),
            "source": SOURCE,
        }
    )

    dividends = raw.get("Dividends", pd.Series(0.0, index=raw.index)).fillna(0.0)
    splits = raw.get("Stock Splits", pd.Series(0.0, index=raw.index)).fillna(0.0)
    action_mask = (dividends != 0.0) | (splits != 0.0)

    actions = pd.DataFrame(
        {
            "symbol": symbol,
            "effective_date": ts[action_mask],
            "knowledge_ts": ts[action_mask],
            "split_ratio": splits[action_mask].replace(0.0, 1.0),
            "dividend": dividends[action_mask],
            "source": SOURCE,
        }
    )

    return prices, actions
