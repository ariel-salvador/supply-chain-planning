import numpy as np
import pytest

from ppsim import mps

LABELS = list(range(6))


def test_projected_demand_uses_orders_inside_dtf():
    f = [10, 10, 10, 10]
    o = [8, 12, 5, 0]
    assert mps.projected_demand(f, o, dtf=2).tolist() == [8, 12, 10, 10]


def test_atp_textbook():
    # OH 50, MPS in weeks 1 and 3, orders 30/40/20/10
    out = mps.atp(50, np.array([0, 100, 0, 100]), np.array([30, 40, 20, 10]))
    assert out.tolist() == [20, 40, 0, 90]


def test_atp_look_ahead_borrows_from_earlier():
    # week-2 receipt of 10 can't cover orders of 40, so 30 is borrowed from week 0
    out = mps.atp(100, np.array([0, 0, 10, 0]), np.array([20, 0, 40, 0]))
    assert out.tolist() == [50, 0, 0, 0]


def test_planning_fence_even_spread():
    out = mps.apply_planning_fence(np.array([10, 20, 30, 30, 30, 30.0]), ptf=2)
    assert out.tolist() == [0, 0, 45, 45, 30, 30]
    assert out.sum() == pytest.approx(150)


def test_planning_fence_capacity_fill():
    out = mps.apply_planning_fence(np.array([10, 20, 30, 30, 30, 30.0]), ptf=2, capacity=40)
    assert out.tolist() == [0, 0, 40, 40, 40, 30]


def test_planning_fence_capacity_counts_firm():
    firm = np.array([0, 0, 35, 0, 0, 0.0])
    out = mps.apply_planning_fence(np.array([10, 0, 0, 0, 0, 0.0]), ptf=2, capacity=40, firm=firm)
    assert out.tolist() == [0, 0, 5, 5, 0, 0]


def test_build_pab_zones_and_validation():
    res = mps.build(
        forecast=[10] * 6, orders=[9, 5, 0, 0, 0, 0], candidate_plan=[10] * 6, firm=[0, 0, 0, 0, 0, 0],
        on_hand=30, dtf=1, ptf=2, labels=LABELS,
    )
    t = res.table
    assert t.loc["projected_demand"].tolist() == [9, 10, 10, 10, 10, 10]
    assert t.loc["planned_mps"].tolist() == [0, 0, 20, 20, 10, 10]
    assert t.loc["projected_available_balance"].tolist() == [21, 11, 21, 31, 31, 31]
    assert res.zones == ["frozen", "slushy", "liquid", "liquid", "liquid", "liquid"]
    assert res.to_frame().loc["zone"].tolist()[0] == "frozen"
    with pytest.raises(ValueError):
        mps.build([1], [0], [0], [0], 0, dtf=2, ptf=1, labels=[0])


def test_mock_orders_decay_and_cap():
    o = mps.mock_orders([100] * 8, booked_first=1.2, decay=0.5, seed=3)
    assert o[0] <= 100  # capped at forecast
    assert o[-1] < o[1]
