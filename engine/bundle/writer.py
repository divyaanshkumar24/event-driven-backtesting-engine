from __future__ import annotations

import hashlib
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from engine.data.store import DataStore

_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def engine_version() -> str:
    with _PYPROJECT_PATH.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def hash_price_data(store: DataStore, symbol: str, start=None, end=None) -> str:
    """A deterministic fingerprint of the exact bars used, so two bundles
    with identical-looking inputs (symbol, dates, params) can still be
    told apart if the underlying cached price data changed.
    """
    df = store.query_all_raw_prices([symbol], start=start, end=end)
    df = df.sort_values(["ts", "source"]).reset_index(drop=True)
    canonical = df.to_csv(index=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_run_id(
    manifest_inputs: dict, data_hash: str, timestamp: datetime | None = None
) -> str:
    """Timestamp-based (so re-running the same config produces a distinct,
    diffable bundle) with a content fingerprint suffix (so two run_ids
    make it obvious at a glance whether their inputs+data were identical).
    """
    ts = timestamp or datetime.now(UTC)
    fingerprint = hashlib.sha256(
        (json.dumps(manifest_inputs, sort_keys=True, default=str) + data_hash).encode("utf-8")
    ).hexdigest()[:10]
    return f"{ts:%Y%m%dT%H%M%S}_{fingerprint}"


def _equity_dataframe(equity_curve: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(equity_curve, columns=["timestamp", "equity"])


def _trades_dataframe(trades: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": t.timestamp,
                "symbol": t.symbol,
                "quantity": t.quantity,
                "fill_price": t.fill_price,
                "commission": t.commission,
                "half_spread": t.half_spread,
                "impact": t.impact,
            }
            for t in trades
        ]
    )


def write_bundle(
    bundles_dir: str | Path,
    run_id: str,
    manifest_inputs: dict,
    metrics: dict,
    equity_curve: list[tuple],
    trades: list,
    sensitivity: dict,
    bias_audit: dict,
    data_hash: str,
    timestamp: datetime | None = None,
) -> Path:
    """Writes bundles_dir/run_<run_id>/ with manifest.json, metrics.json,
    equity.parquet, trades.parquet, sensitivity.json, bias_audit.json.
    Refuses to overwrite an existing bundle directory — bundles are
    immutable once written; re-running produces a new run_id instead.
    """
    bundle_dir = Path(bundles_dir) / f"run_{run_id}"
    if bundle_dir.exists():
        raise FileExistsError(
            f"bundle {bundle_dir} already exists; bundles are immutable, use a new run_id"
        )
    bundle_dir.mkdir(parents=True)

    manifest = {
        "run_id": run_id,
        "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
        "engine_version": engine_version(),
        "data_hash": data_hash,
        "inputs": manifest_inputs,
    }

    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    (bundle_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    (bundle_dir / "sensitivity.json").write_text(json.dumps(sensitivity, indent=2, default=str))
    (bundle_dir / "bias_audit.json").write_text(json.dumps(bias_audit, indent=2, default=str))
    _equity_dataframe(equity_curve).to_parquet(bundle_dir / "equity.parquet", index=False)
    _trades_dataframe(trades).to_parquet(bundle_dir / "trades.parquet", index=False)

    return bundle_dir
