import json
from datetime import datetime, timedelta

from engine.bundle.viewer_export import export_bundle_for_viewer
from engine.bundle.writer import write_bundle
from engine.portfolio.portfolio import Trade

from tests.walkforward.helpers import SYMBOL, seed_store


def _curve(values, base=None):
    base = base or datetime(2020, 1, 1)
    return [(base + timedelta(days=i), v) for i, v in enumerate(values)]


def test_export_bundle_for_viewer_produces_aligned_equity_and_copies_json(tmp_path):
    store, ts = seed_store([100.0, 102.0, 101.0, 105.0, 108.0])
    net_curve = _curve([100_000, 100_500, 100_200, 101_000, 102_000], base=ts[0])
    gross_curve = _curve([100_000, 100_600, 100_400, 101_300, 102_500], base=ts[0])

    bundle_dir = write_bundle(
        tmp_path / "bundles",
        "abc",
        manifest_inputs={"symbol": SYMBOL},
        metrics={"sharpe": 1.0},
        equity_curve=net_curve,
        trades=[Trade(ts[1], SYMBOL, 100, 102.0, 1.0, 0.5, 0.0)],
        sensitivity={"param_grid": []},
        bias_audit={"look_ahead_violations": {"status": "pass", "value": 0, "explanation": "x"}},
        data_hash="deadbeef",
    )

    output_dir = tmp_path / "viewer_data"
    export_bundle_for_viewer(
        bundle_dir, store, SYMBOL, net_curve, gross_curve, 100_000.0, output_dir
    )

    for name in [
        "manifest.json",
        "metrics.json",
        "sensitivity.json",
        "bias_audit.json",
        "equity.json",
        "trades.json",
    ]:
        assert (output_dir / name).exists()

    equity = json.loads((output_dir / "equity.json").read_text())
    assert len(equity) == 5
    assert set(equity[0].keys()) == {"timestamp", "net", "gross", "benchmark"}
    # benchmark starts at initial_cash (first bar), tracks the underlying's own return thereafter
    assert equity[0]["benchmark"] == 100_000.0
    expected_last_benchmark = 100_000.0 * (108.0 / 100.0)
    assert equity[-1]["benchmark"] == expected_last_benchmark

    trades = json.loads((output_dir / "trades.json").read_text())
    assert len(trades) == 1
    assert trades[0]["symbol"] == SYMBOL

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["run_id"] == "abc"


def test_export_drops_dates_without_price_coverage(tmp_path):
    """If the net/gross curve extends beyond the store's cached price
    range, those rows are dropped rather than producing a malformed
    benchmark point.
    """
    store, ts = seed_store([100.0, 102.0, 101.0])
    net_curve = _curve(
        [100_000, 100_500, 100_200, 101_000], base=ts[0]
    )  # one extra day beyond the store
    gross_curve = _curve([100_000, 100_600, 100_400, 101_300], base=ts[0])

    bundle_dir = write_bundle(
        tmp_path / "bundles",
        "xyz",
        manifest_inputs={"symbol": SYMBOL},
        metrics={},
        equity_curve=net_curve,
        trades=[],
        sensitivity={},
        bias_audit={},
        data_hash="deadbeef",
    )

    output_dir = tmp_path / "viewer_data"
    export_bundle_for_viewer(
        bundle_dir, store, SYMBOL, net_curve, gross_curve, 100_000.0, output_dir
    )

    equity = json.loads((output_dir / "equity.json").read_text())
    assert len(equity) == 3


def test_export_creates_output_dir_if_missing(tmp_path):
    store, ts = seed_store([100.0, 101.0])
    curve = _curve([100_000, 100_100], base=ts[0])

    bundle_dir = write_bundle(
        tmp_path / "bundles",
        "nested",
        manifest_inputs={},
        metrics={},
        equity_curve=curve,
        trades=[],
        sensitivity={},
        bias_audit={},
        data_hash="hash",
    )

    output_dir = tmp_path / "does" / "not" / "exist" / "yet"
    result = export_bundle_for_viewer(
        bundle_dir, store, SYMBOL, curve, curve, 100_000.0, output_dir
    )

    assert result == output_dir
    assert (output_dir / "equity.json").exists()
