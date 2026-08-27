from datetime import datetime, timedelta

from engine.metrics.trades import avg_loss, avg_win, exposure, hit_rate, reconstruct_round_trips
from engine.portfolio.portfolio import Trade


def _trade(day, symbol, quantity, price, commission=0.0, half_spread=0.0, impact=0.0):
    return Trade(
        timestamp=datetime(2020, 1, 1) + timedelta(days=day),
        symbol=symbol,
        quantity=quantity,
        fill_price=price,
        commission=commission,
        half_spread=half_spread,
        impact=impact,
    )


def test_simple_full_open_close_round_trip():
    trades = [
        _trade(0, "AAA", 100, 50.0),  # buy 100 @ 50
        _trade(5, "AAA", -100, 55.0),  # sell 100 @ 55
    ]
    round_trips = reconstruct_round_trips(trades)

    assert len(round_trips) == 1
    rt = round_trips[0]
    assert rt.quantity == 100
    assert rt.entry_price == 50.0
    assert rt.exit_price == 55.0
    assert rt.realized_pnl == 500.0  # (55-50)*100, no costs


def test_round_trip_nets_out_allocated_costs():
    trades = [
        _trade(0, "AAA", 100, 50.0, commission=10.0),
        _trade(5, "AAA", -100, 55.0, commission=10.0),
    ]
    round_trips = reconstruct_round_trips(trades)
    assert round_trips[0].realized_pnl == 500.0 - 20.0


def test_partial_close_leaves_remaining_lot_open():
    trades = [
        _trade(0, "AAA", 100, 50.0),
        _trade(5, "AAA", -40, 55.0),  # only closes 40 of the 100
    ]
    round_trips = reconstruct_round_trips(trades)

    assert len(round_trips) == 1
    assert round_trips[0].quantity == 40
    assert round_trips[0].realized_pnl == (55.0 - 50.0) * 40


def test_position_flip_produces_a_close_and_a_new_open_lot():
    trades = [
        _trade(0, "AAA", 100, 50.0),  # long 100
        _trade(5, "AAA", -150, 55.0),  # closes the 100, opens short 50
        _trade(10, "AAA", 50, 52.0),  # closes the short 50
    ]
    round_trips = reconstruct_round_trips(trades)

    assert len(round_trips) == 2
    assert round_trips[0].quantity == 100
    assert round_trips[0].realized_pnl == (55.0 - 50.0) * 100
    assert round_trips[1].quantity == 50
    # short lot: profit when exit_price < entry_price
    assert round_trips[1].realized_pnl == (55.0 - 52.0) * 50


def test_hit_rate_avg_win_avg_loss():
    trades = [
        _trade(0, "AAA", 100, 50.0),
        _trade(1, "AAA", -100, 55.0),  # win: +500
        _trade(2, "AAA", 100, 60.0),
        _trade(3, "AAA", -100, 58.0),  # loss: -200
    ]
    round_trips = reconstruct_round_trips(trades)

    assert hit_rate(round_trips) == 0.5
    assert avg_win(round_trips) == 500.0
    assert avg_loss(round_trips) == -200.0


def test_hit_rate_none_when_no_round_trips():
    assert hit_rate([]) is None
    assert avg_win([]) is None
    assert avg_loss([]) is None


def test_exposure_counts_bars_with_a_nonzero_position():
    base = datetime(2020, 1, 1)
    equity_curve = [(base + timedelta(days=i), 100_000.0) for i in range(6)]
    trades = [
        _trade(1, "AAA", 100, 50.0),  # position opens on day 1
        _trade(4, "AAA", -100, 55.0),  # position closes on day 4
    ]
    # exposed on days 1,2,3 (position open, before the closing trade lands on day 4)
    assert exposure(trades, equity_curve) == 3 / 6


def test_exposure_is_zero_with_no_trades():
    base = datetime(2020, 1, 1)
    equity_curve = [(base + timedelta(days=i), 100_000.0) for i in range(3)]
    assert exposure([], equity_curve) == 0.0
