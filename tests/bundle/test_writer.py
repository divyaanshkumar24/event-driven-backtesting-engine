import json
from datetime import datetime

import pandas as pd
import pytest
from engine.bundle.writer import engine_version, generate_run_id, hash_price_data, write_bundle
from engine.portfolio.portfolio import Trade

from tests.walkforward.helpers import SYMBOL, seed_store


def _sample_bundle_args():
    equity_curve = [(datetime(2020, 1, 1 + i), 100_000.0 + i * 10) for i in range(5)]
    trades = [Trade(datetime(2020, 1, 2), SYMBOL, 10, 100.0, 1.0, 0.5, 0.0)]
    metrics = {"sharpe": 1.2}
    sensitivity = {"param_grid": [], "rebalance_frequency": []}
    bias_audit = {"look_ahead_violations": {"status": "pass", "value": 0, "explanation": "x"}}
    return equity_curve, trades, metrics, sensitivity, bias_audit


def test_engine_version_matches_pyproject():
    version = engine_version()
    assert version == "0.1.0"


def test_hash_price_data_is_deterministic_and_order_independent():
    store, _ = seed_store([100.0, 101.0, 99.0, 102.0])
    h1 = hash_price_data(store, SYMBOL)
    h2 = hash_price_data(store, SYMBOL)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex digest


def test_hash_price_data_changes_when_data_changes():
    store_a, _ = seed_store([100.0, 101.0, 99.0])
    store_b, _ = seed_store([100.0, 101.0, 200.0])
    assert hash_price_data(store_a, SYMBOL) != hash_price_data(store_b, SYMBOL)


def test_generate_run_id_is_deterministic_for_identical_inputs():
    ts = datetime(2024, 1, 1, 12, 0, 0)
    inputs = {"symbol": "AAA", "short_window": 5}
    run_id_a = generate_run_id(inputs, "abc123", timestamp=ts)
    run_id_b = generate_run_id(inputs, "abc123", timestamp=ts)
    assert run_id_a == run_id_b


def test_generate_run_id_differs_when_inputs_differ():
    ts = datetime(2024, 1, 1, 12, 0, 0)
    run_id_a = generate_run_id({"short_window": 5}, "abc123", timestamp=ts)
    run_id_b = generate_run_id({"short_window": 10}, "abc123", timestamp=ts)
    assert run_id_a != run_id_b


def test_write_bundle_produces_all_required_files(tmp_path):
    equity_curve, trades, metrics, sensitivity, bias_audit = _sample_bundle_args()

    bundle_dir = write_bundle(
        tmp_path,
        "test123",
        manifest_inputs={"symbol": SYMBOL},
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        sensitivity=sensitivity,
        bias_audit=bias_audit,
        data_hash="deadbeef",
    )

    assert bundle_dir == tmp_path / "run_test123"
    expected_files = {
        "manifest.json",
        "metrics.json",
        "equity.parquet",
        "trades.parquet",
        "sensitivity.json",
        "bias_audit.json",
    }
    assert {p.name for p in bundle_dir.iterdir()} == expected_files

    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    assert manifest["run_id"] == "test123"
    assert manifest["data_hash"] == "deadbeef"
    assert manifest["inputs"] == {"symbol": SYMBOL}
    assert manifest["engine_version"] == "0.1.0"

    equity_df = pd.read_parquet(bundle_dir / "equity.parquet")
    assert list(equity_df.columns) == ["timestamp", "equity"]
    assert len(equity_df) == 5

    trades_df = pd.read_parquet(bundle_dir / "trades.parquet")
    assert len(trades_df) == 1
    assert trades_df.iloc[0]["symbol"] == SYMBOL


def test_write_bundle_refuses_to_overwrite_an_existing_run(tmp_path):
    equity_curve, trades, metrics, sensitivity, bias_audit = _sample_bundle_args()
    kwargs = dict(
        manifest_inputs={"symbol": SYMBOL},
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        sensitivity=sensitivity,
        bias_audit=bias_audit,
        data_hash="deadbeef",
    )

    write_bundle(tmp_path, "dup", **kwargs)
    with pytest.raises(FileExistsError):
        write_bundle(tmp_path, "dup", **kwargs)
