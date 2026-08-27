from __future__ import annotations

from pathlib import Path

import pandas as pd

from engine.data.store import DataStore


def export_bundle_for_viewer(
    bundle_dir: Path,
    store: DataStore,
    symbol: str,
    net_equity_curve: list[tuple],
    gross_equity_curve: list[tuple],
    initial_cash: float,
    output_dir: Path,
) -> Path:
    """Writes a browser-ready copy of `bundle_dir`'s data into `output_dir`
    (viewer/public/data/current/), plus a merged equity series with a
    buy-and-hold benchmark overlay derived from the underlying's raw
    prices over the same OOS date range.

    This is a viewer-side convenience artifact, not part of the immutable
    bundle contract written by write_bundle — the bundle directory itself
    is untouched. The gross curve and benchmark curve aren't persisted in
    the bundle (only their summary stats are, in metrics.json/bias_audit
    .json), so they're rebuilt here from data already in memory from the
    same run, rather than re-running anything.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for name in ("manifest.json", "metrics.json", "sensitivity.json", "bias_audit.json"):
        (output_dir / name).write_text((bundle_dir / name).read_text())

    net_df = pd.DataFrame(net_equity_curve, columns=["timestamp", "equity"]).set_index("timestamp")
    gross_df = pd.DataFrame(gross_equity_curve, columns=["timestamp", "equity"]).set_index(
        "timestamp"
    )

    start, end = net_df.index.min(), net_df.index.max()
    prices = store.query_all_raw_prices([symbol], start=start, end=end).sort_values("ts")
    price_series = prices.set_index("ts")["close"]
    benchmark = initial_cash * (price_series / price_series.iloc[0])

    merged = pd.DataFrame(
        {"net": net_df["equity"], "gross": gross_df["equity"], "benchmark": benchmark}
    ).dropna()
    merged.index.name = "timestamp"
    merged = merged.reset_index()
    merged["timestamp"] = merged["timestamp"].astype(str)
    (output_dir / "equity.json").write_text(merged.to_json(orient="records"))

    trades_df = pd.read_parquet(bundle_dir / "trades.parquet")
    if not trades_df.empty:
        trades_df["timestamp"] = trades_df["timestamp"].astype(str)
    (output_dir / "trades.json").write_text(trades_df.to_json(orient="records"))

    return output_dir
