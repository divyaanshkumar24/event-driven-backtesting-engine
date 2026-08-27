import json
import math

import pytest
from engine.audit.bias_audit import build_bias_audit, write_bias_audit
from engine.costs.model import CommissionModel, CostModel, ImpactModel, SpreadModel
from engine.walkforward.runner import run_walk_forward
from engine.walkforward.windows import WalkForwardConfig

from tests.walkforward.helpers import SYMBOL, seed_store, sma_factory

GRID = {"short_window": [3, 5], "long_window": [15, 20]}
POSITIVE_COST_MODEL = CostModel(
    commission=CommissionModel(mode="per_share", per_share=0.005),
    spread=SpreadModel(half_spread_bps=5.0),
    impact=ImpactModel(y=0.1),
)

EXPECTED_FIELDS = {
    "look_ahead_violations",
    "fill_timing_assumption",
    "survivorship_posture",
    "cost_analysis",
    "turnover",
    "overfitting_analysis",
    "is_oos_degradation",
    "regime_breakdown",
    "capacity",
}


def _oscillating_prices(n=140):
    return [100.0 + 10 * math.sin(i / 5) + 0.1 * i for i in range(n)]


@pytest.fixture(scope="module")
def audit_fixture():
    store, ts = seed_store(_oscillating_prices())
    config = WalkForwardConfig(train_bars=40, test_bars=15, purge_bars=3, embargo_bars=2)
    result = run_walk_forward(
        store, SYMBOL, sma_factory, GRID, config, POSITIVE_COST_MODEL, initial_cash=100_000.0
    )
    audit = build_bias_audit(
        store, SYMBOL, sma_factory, result, POSITIVE_COST_MODEL, initial_cash=100_000.0
    )
    return store, result, audit


def test_audit_has_exactly_the_required_fields_each_with_status_value_explanation(audit_fixture):
    _, _, audit = audit_fixture

    assert set(audit.keys()) == EXPECTED_FIELDS
    for name, field in audit.items():
        assert set(field.keys()) == {"status", "value", "explanation"}, name
        assert isinstance(field["explanation"], str) and field["explanation"]


def test_look_ahead_violations_is_zero_by_construction(audit_fixture):
    _, _, audit = audit_fixture
    assert audit["look_ahead_violations"]["value"] == 0
    assert audit["look_ahead_violations"]["status"] == "pass"


def test_fill_timing_assumption_matches_the_fixed_convention(audit_fixture):
    _, _, audit = audit_fixture
    assert audit["fill_timing_assumption"]["value"] == "next-bar-open"


def test_survivorship_posture_flags_limited_on_free_data_with_no_delistings(audit_fixture):
    _, _, audit = audit_fixture
    assert audit["survivorship_posture"]["value"] == "survivorship-limited"
    assert audit["survivorship_posture"]["status"] == "flagged"


def test_cost_analysis_net_sharpe_does_not_exceed_gross_sharpe(audit_fixture):
    _, _, audit = audit_fixture
    value = audit["cost_analysis"]["value"]
    assert value["net_sharpe"] <= value["gross_sharpe"]
    assert value["annualized_cost_drag"] >= 0


def test_turnover_is_non_negative(audit_fixture):
    _, _, audit = audit_fixture
    assert audit["turnover"]["value"] >= 0


def test_overfitting_analysis_reports_combo_count_and_dsr(audit_fixture):
    _, result, audit = audit_fixture
    value = audit["overfitting_analysis"]["value"]
    assert value["n_param_combos_tested_per_fold"] == len(GRID["short_window"]) * len(
        GRID["long_window"]
    )
    assert value["n_folds"] == len(result.folds)
    assert 0.0 <= value["deflated_sharpe"]["dsr"] <= 1.0


def test_is_oos_degradation_reports_both_sharpes(audit_fixture):
    _, _, audit = audit_fixture
    value = audit["is_oos_degradation"]["value"]
    assert "is_sharpe_avg" in value
    assert "oos_sharpe" in value
    assert math.isclose(value["degradation"], value["is_sharpe_avg"] - value["oos_sharpe"])


def test_write_bias_audit_produces_valid_json_matching_the_schema(audit_fixture, tmp_path):
    _, _, audit = audit_fixture
    path = tmp_path / "bias_audit.json"

    write_bias_audit(path, audit)

    loaded = json.loads(path.read_text())
    assert set(loaded.keys()) == EXPECTED_FIELDS
