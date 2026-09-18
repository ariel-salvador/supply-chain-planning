import numpy as np
import pandas as pd
import pytest

from ppsim import sop


def weeks(start="2027-01-04", n=9):
    return pd.period_range(start=start, periods=n, freq="W-SUN")


def test_week_month_weights_rows_sum_to_one_and_split_by_days():
    w = sop.week_month_weights(weeks())
    assert np.allclose(w.sum(axis=1), 1)
    # week of 2027-01-25..31 is all January; 2027-02-01..07 all February
    assert w.iloc[3][pd.Period("2027-01", "M")] == pytest.approx(1)
    # 2027-03-01 is a Monday, so no week straddles Feb/Mar; test a straddling week instead
    w2 = sop.week_month_weights(pd.period_range(start="2027-03-29", periods=1, freq="W-SUN"))
    assert w2.iloc[0][pd.Period("2027-03", "M")] == pytest.approx(3 / 7)
    assert w2.iloc[0][pd.Period("2027-04", "M")] == pytest.approx(4 / 7)


def test_aggregate_disaggregate_conserve_totals():
    wk = weeks(n=13)
    w = sop.week_month_weights(wk)
    rng = np.random.default_rng(0)
    weekly = rng.uniform(50, 150, len(wk))
    monthly = sop.aggregate(weekly, w)
    assert monthly.sum() == pytest.approx(weekly.sum())
    back = sop.disaggregate(monthly, weekly, w)
    assert np.allclose(back, weekly)  # disaggregating demand by itself returns it
    plan = monthly * 1.1
    assert sop.disaggregate(plan, weekly, w).sum() == pytest.approx(plan.sum())


def test_days_per_month_counts_partial_edges():
    days = sop.days_per_month(sop.week_month_weights(weeks(n=4)))  # Jan 4..31
    assert days.iloc[0] == pytest.approx(28)


def idx(n):
    return pd.period_range("2027-01", periods=n, freq="M")


def test_chase_hits_target_every_month():
    d = pd.Series([100.0, 200.0, 150.0], index=idx(3))
    days = pd.Series([sop.DAYS_PER_MONTH] * 3, index=idx(3))
    p = sop.plan(d, opening_inventory=50, target_cover_months=0.5, strategy="chase", days=days)
    assert p["target_inventory"].tolist() == pytest.approx([100, 75, 75])
    assert p["ending_inventory"].tolist() == pytest.approx([100, 75, 75])
    assert p["production"].tolist() == pytest.approx([150, 175, 150])
    assert not p["stockout"].any()


def test_level_is_constant_and_reaches_final_target():
    d = pd.Series([100.0, 200.0, 150.0], index=idx(3))
    p = sop.plan(d, 50, 0.5, "level")
    assert p["production"].nunique() == 1
    assert p["ending_inventory"].iloc[-1] == pytest.approx(p["target_inventory"].iloc[-1])


def test_capacity_caps_and_flags():
    d = pd.Series([100.0, 300.0], index=idx(2))
    cap = pd.Series([200.0, 200.0], index=idx(2))
    p = sop.plan(d, 0, 0, "chase", capacity=cap)
    assert p["production"].tolist() == [100, 200]
    assert p["capacity_limited"].tolist() == [False, True]
    assert p["stockout"].tolist() == [False, True]
    assert p["utilization"].tolist() == pytest.approx([0.5, 1.0])


def test_partial_month_target_uses_daily_rate():
    d = pd.Series([100.0, 50.0], index=idx(2))
    days = pd.Series([sop.DAYS_PER_MONTH, sop.DAYS_PER_MONTH / 2], index=idx(2))  # second month half covered
    p = sop.plan(d, 0, 1.0, "chase", days=days)
    assert p["target_inventory"].iloc[0] == pytest.approx(100)  # full-month equivalent, not 50


def test_unknown_strategy():
    with pytest.raises(ValueError):
        sop.plan(pd.Series([1.0], index=idx(1)), 0, 0, "hybrid")
