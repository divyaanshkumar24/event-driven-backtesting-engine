from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import duckdb
import pandas as pd

RAW_PRICES_COLUMNS = [
    "symbol",
    "ts",
    "knowledge_ts",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
]

ADJUSTMENT_FACTORS_COLUMNS = [
    "symbol",
    "effective_date",
    "knowledge_ts",
    "split_ratio",
    "dividend",
    "source",
]

_RAW_PRICES_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_prices (
    symbol VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    knowledge_ts TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (symbol, ts, source)
)
"""

_ADJUSTMENT_FACTORS_SCHEMA = """
CREATE TABLE IF NOT EXISTS adjustment_factors (
    symbol VARCHAR NOT NULL,
    effective_date TIMESTAMP NOT NULL,
    knowledge_ts TIMESTAMP NOT NULL,
    split_ratio DOUBLE NOT NULL DEFAULT 1.0,
    dividend DOUBLE NOT NULL DEFAULT 0.0,
    source VARCHAR NOT NULL,
    PRIMARY KEY (symbol, effective_date, source)
)
"""


class DataStore:
    """DuckDB-backed store. Raw prices and adjustment factors are kept in
    separate tables so a back-adjusted series is never the only record of
    the truth — adjustments are applied on top of raw prices, never baked
    into what gets persisted.
    """

    def __init__(self, path: str | Path = ":memory:"):
        self._conn = duckdb.connect(str(path))
        self._conn.execute(_RAW_PRICES_SCHEMA)
        self._conn.execute(_ADJUSTMENT_FACTORS_SCHEMA)

    def insert_raw_prices(self, df: pd.DataFrame) -> None:
        self._insert("raw_prices", df, RAW_PRICES_COLUMNS)

    def insert_adjustment_factors(self, df: pd.DataFrame) -> None:
        self._insert("adjustment_factors", df, ADJUSTMENT_FACTORS_COLUMNS)

    def _insert(self, table: str, df: pd.DataFrame, columns: list[str]) -> None:
        if df.empty:
            return
        view_name = f"_incoming_{table}"
        self._conn.register(view_name, df[columns])
        cols = ", ".join(columns)
        self._conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {view_name}")
        self._conn.unregister(view_name)

    def has_symbol(self, symbol: str, source: str) -> bool:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM raw_prices WHERE symbol = ? AND source = ?",
            [symbol, source],
        ).fetchone()
        return row[0] > 0

    def query_as_of(self, symbol: str, t) -> pd.DataFrame:
        """Rows with knowledge_ts <= t, and nothing else. This is the sole
        read path a strategy is meant to use; it can never return a row
        whose knowledge_ts is after t.
        """
        return self._conn.execute(
            f"SELECT {', '.join(RAW_PRICES_COLUMNS)} FROM raw_prices "
            "WHERE symbol = ? AND knowledge_ts <= ? ORDER BY ts",
            [symbol, t],
        ).df()

    def query_all_raw_prices(self, symbols: Iterable[str], start=None, end=None) -> pd.DataFrame:
        """All bars for `symbols`, optionally bounded to knowledge_ts in
        [start, end] (either bound may be omitted). Used both for the full
        replay stream and for a walk-forward fold's restricted train/test
        windows.
        """
        symbols = list(symbols)
        if not symbols:
            return pd.DataFrame(columns=RAW_PRICES_COLUMNS)
        placeholders = ", ".join("?" for _ in symbols)
        clauses = [f"symbol IN ({placeholders})"]
        params: list = list(symbols)
        if start is not None:
            clauses.append("knowledge_ts >= ?")
            params.append(start)
        if end is not None:
            clauses.append("knowledge_ts <= ?")
            params.append(end)
        where = " AND ".join(clauses)
        return self._conn.execute(
            f"SELECT {', '.join(RAW_PRICES_COLUMNS)} FROM raw_prices "
            f"WHERE {where} ORDER BY knowledge_ts, symbol",
            params,
        ).df()

    def query_adjustment_factors(self, symbol: str) -> pd.DataFrame:
        return self._conn.execute(
            f"SELECT {', '.join(ADJUSTMENT_FACTORS_COLUMNS)} FROM adjustment_factors "
            "WHERE symbol = ? ORDER BY effective_date",
            [symbol],
        ).df()
