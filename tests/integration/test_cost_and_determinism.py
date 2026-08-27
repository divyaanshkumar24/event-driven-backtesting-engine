from engine.costs.model import ZERO_COST_MODEL, CommissionModel, CostModel, ImpactModel, SpreadModel

from tests.integration.helpers import run_full_backtest, sharpe

POSITIVE_COST_MODEL = CostModel(
    commission=CommissionModel(mode="per_share", per_share=0.01),
    spread=SpreadModel(half_spread_bps=10.0),
    impact=ImpactModel(y=0.2),
)


def test_net_sharpe_is_non_increasing_in_costs():
    gross = run_full_backtest(ZERO_COST_MODEL)
    net = run_full_backtest(POSITIVE_COST_MODEL)

    assert len(gross.trades) > 0, (
        "test setup should produce trades to make the comparison meaningful"
    )
    assert len(net.trades) > 0
    assert sharpe(net.equity_curve) <= sharpe(gross.equity_curve)


def test_determinism_same_inputs_produce_identical_results():
    run_a = run_full_backtest(POSITIVE_COST_MODEL)
    run_b = run_full_backtest(POSITIVE_COST_MODEL)

    assert run_a.equity_curve == run_b.equity_curve
    assert run_a.cash == run_b.cash

    trades_a = [(t.timestamp, t.symbol, t.quantity, t.fill_price) for t in run_a.trades]
    trades_b = [(t.timestamp, t.symbol, t.quantity, t.fill_price) for t in run_b.trades]
    assert trades_a == trades_b
