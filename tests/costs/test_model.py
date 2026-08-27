import pandas as pd
from engine.costs.model import CommissionModel, CostModel, ImpactModel, SpreadModel


def test_commission_per_share():
    model = CommissionModel(mode="per_share", per_share=0.01)
    assert model.compute(quantity=100, price=50.0) == 1.0
    assert model.compute(quantity=-100, price=50.0) == 1.0


def test_commission_per_trade():
    model = CommissionModel(mode="per_trade", per_trade=1.5)
    assert model.compute(quantity=1, price=50.0) == 1.5
    assert model.compute(quantity=1000, price=50.0) == 1.5


def test_commission_bps():
    model = CommissionModel(mode="bps", bps=10.0)
    # 100 shares * $50 = $5000 notional; 10bps = 0.001 -> $5.00
    assert model.compute(quantity=100, price=50.0) == 5.0


def test_half_spread_cost():
    model = SpreadModel(half_spread_bps=5.0)
    # 100 shares * $50 = $5000 notional; 5bps = 0.0005 -> $2.50
    assert model.compute(quantity=100, price=50.0) == 2.5


def test_impact_zero_when_no_adv():
    model = ImpactModel(y=0.1)
    assert model.compute(quantity=100, price=50.0, sigma=0.02, adv=0.0) == 0.0


def test_impact_matches_square_root_formula():
    model = ImpactModel(y=0.1)
    quantity, price, sigma, adv = 100.0, 50.0, 0.02, 1_000_000.0
    expected_fraction = 0.1 * 0.02 * (quantity / adv) ** 0.5
    expected_cost = expected_fraction * price * quantity
    assert model.compute(quantity, price, sigma, adv) == expected_cost


def test_cost_model_breakdown_sums_to_total():
    history = pd.DataFrame(
        {
            "close": [100.0, 101.0, 99.0, 102.0, 103.0],
            "volume": [1_000_000.0] * 5,
        }
    )
    model = CostModel()
    breakdown = model.compute(quantity=100, price=100.0, history=history)
    assert breakdown.total == breakdown.commission + breakdown.half_spread + breakdown.impact
    assert breakdown.commission > 0
    assert breakdown.half_spread > 0


def test_cost_model_impact_uses_only_trailing_history_within_lookback():
    # A huge early outlier return outside the lookback window must not
    # move sigma; only the trailing `impact_lookback` bars should count.
    far_past = [100.0] * 50 + [1000.0]  # one huge jump, well before the tail
    recent_flat = [50.0] * 25  # flat trailing window -> sigma == 0
    history = pd.DataFrame(
        {
            "close": far_past + recent_flat,
            "volume": [1_000_000.0] * (len(far_past) + len(recent_flat)),
        }
    )
    model = CostModel(impact_lookback=20)
    breakdown = model.compute(quantity=100, price=50.0, history=history)
    assert breakdown.impact == 0.0
