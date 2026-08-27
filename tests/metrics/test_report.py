from datetime import datetime, timedelta

from engine.metrics.report import compute_metrics
from engine.portfolio.portfolio import Trade

EXPECTED_KEYS = {
    "cagr",
    "sharpe",
    "sortino",
    "calmar",
    "max_drawdown",
    "max_drawdown_duration",
    "hit_rate",
    "avg_win",
    "avg_loss",
    "exposure",
    "turnover",
    "deflated_sharpe",
    "gross_vs_net",
}


def _curve(values):
    base = datetime(2020, 1, 1)
    return [(base + timedelta(days=i), v) for i, v in enumerate(values)]


def test_compute_metrics_has_the_full_required_set():
    net_curve = _curve([100_000 * (1.0005**i) for i in range(60)])
    gross_curve = _curve([100_000 * (1.0007**i) for i in range(60)])
    trades = [
        Trade(datetime(2020, 1, 5), "AAA", 100, 50.0, 1.0, 0.5, 0.0),
        Trade(datetime(2020, 1, 20), "AAA", -100, 55.0, 1.0, 0.5, 0.0),
    ]
    dsr = {
        "dsr": 0.9,
        "observed_sharpe": 1.0,
        "benchmark_sharpe_under_null": 0.2,
        "n_trials": 4,
        "n_obs": 59,
    }

    metrics = compute_metrics(net_curve, gross_curve, trades, dsr)

    assert set(metrics.keys()) == EXPECTED_KEYS
    assert metrics["deflated_sharpe"] == dsr
    assert metrics["gross_vs_net"]["gross_sharpe"] >= metrics["gross_vs_net"]["net_sharpe"]
    assert metrics["hit_rate"] == 1.0
    assert metrics["avg_win"] == 500.0 - 3.0
    assert metrics["avg_loss"] is None
