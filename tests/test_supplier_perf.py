"""Supplier scorecard, safety-stock cost, single vs dual source, forward buy vs spot.

Fixture (conftest): item B, 18 units per weekly bucket (936/yr), awarded to s1 at
13.20 landed; 4 simulated delivery periods, zero price drift, short shipments deliver
half the order, z = 2, carrying 20%/yr, dual split 50/50, disruption 2 weeks at
P = 1.0 x (1 - risk score) -> s1 (low, 0.9) 0.10, s2 (high, 0.1) 0.90.
"""
import math

import numpy as np
import pandas as pd
import pytest

from ppsim import supplier_perf as perf
from ppsim.pipeline import run


@pytest.fixture
def res(sourcing_cfg):
    return run(sourcing_cfg, fetch_prices=False)


def with_quote(res, **overrides):
    """The quotes frame with the awarded supplier's terms overridden."""
    q = res.quotes.copy()
    row = q["supplier"] == res.awards.loc["B", "awarded_to"]
    for k, v in overrides.items():
        q.loc[row, k] = v
    return q


# --- M6e scorecard --------------------------------------------------------


@pytest.mark.parametrize("otif,expected", [(1.0, "A"), (0.95, "A"), (0.949, "B"), (0.90, "B"), (0.899, "C"), (0.80, "C"), (0.799, "D"), (0.0, "D")])
def test_grade_bands(otif, expected):
    assert perf.grade(otif) == expected


def test_history_of_a_perfect_supplier(res):
    h = res.delivery_history
    assert len(h) == 4                                    # scorecard_periods
    assert h["on_time"].all() and h["in_full"].all()      # quoted OTIF 1.0, no short ships
    assert (h["actual_lead_time"] == h["promised_lead_time"]).all()
    assert (h["weeks_late"] == 0).all()
    assert h["ppv_usd"].abs().max() == 0                  # zero price drift in the fixture
    sc = res.scorecard.loc[("B", "s1")]
    assert sc["otif_pct"] == 1.0 and sc["grade"] == "A"
    assert sc["fill_rate"] == 1.0 and sc["ppv_pct"] == 0.0
    assert sc["standard_spend_usd"] == pytest.approx(4 * 18 * 13.2)


def test_short_shipments_cut_fill_rate_but_not_on_time(res, sourcing_cfg):
    q = with_quote(res, otif=0.5, short_ship_rate=0.5)
    h = perf.delivery_history(sourcing_cfg, q, res.awards, res.usage)
    # on-time frequency = OTIF / (1 - short-ship rate) = 1.0, so lateness is not the problem
    assert h["on_time"].all()
    assert (h["otif"] == h["in_full"]).all()
    short = (~h["in_full"]).sum()
    assert h["received_qty"].sum() == pytest.approx((4 - short) * 18 + short * 9)
    sc = perf.scorecard(sourcing_cfg, h, q).loc[("B", "s1")]
    assert sc["fill_rate"] == pytest.approx(1 - 0.5 * short / 4)
    assert sc["otif_vs_quoted"] == pytest.approx(sc["otif_pct"] - 0.5)


def test_every_delivery_late_when_nothing_arrives_in_full(res, sourcing_cfg):
    q = with_quote(res, otif=0.4, short_ship_rate=1.0, lead_time_sigma=2.0)
    h = perf.delivery_history(sourcing_cfg, q, res.awards, res.usage)
    assert not h["on_time"].any() and not h["in_full"].any()
    assert (h["weeks_late"] >= 1).all()                   # a late delivery always slips a full bucket
    assert (h["actual_lead_time"] > h["promised_lead_time"]).all()
    assert perf.scorecard(sourcing_cfg, h, q).loc[("B", "s1"), "grade"] == "D"


def test_purchase_price_variance_is_measured_against_standard_cost(res, sourcing_cfg):
    cfg = sourcing_cfg
    drifting = type(cfg.sourcing)(**{**cfg.sourcing.__dict__, "price_drift_cv": 0.1})
    cfg = type(cfg)(**{**cfg.__dict__, "sourcing": drifting})
    h = perf.delivery_history(cfg, res.quotes, res.awards, res.usage)
    assert h["ppv_usd"].abs().sum() > 0
    expected = ((h["actual_usd_per_uom"] - h["standard_usd_per_uom"]) * h["received_qty"]).sum()
    sc = perf.scorecard(cfg, h, res.quotes).loc[("B", "s1")]
    assert sc["ppv_usd"] == pytest.approx(expected)
    assert sc["ppv_pct"] == pytest.approx(expected / sc["standard_spend_usd"])


def test_history_is_reproducible_from_the_seed(res, sourcing_cfg):
    again = perf.delivery_history(sourcing_cfg, res.quotes, res.awards, res.usage)
    pd.testing.assert_frame_equal(res.delivery_history, again)


# --- M6f safety stock, single vs dual, forward buy ------------------------


def test_safety_stock_cost_prices_lead_time_variability(res):
    ss = res.safety_stock.set_index("supplier")
    # safety stock = z (2) x lead-time sigma x demand per bucket (18)
    assert ss.loc[["s1", "s2", "s3"], "safety_stock_qty"].tolist() == [0.0, 36.0, 72.0]
    assert ss.loc["s2", "annual_carrying_usd"] == pytest.approx(36 * ss.loc["s2", "landed_usd_per_uom"] * 0.2)
    assert bool(ss.loc["s1", "awarded"]) and not bool(ss.loc["s2", "awarded"])
    # the awarded supplier quotes a stable lead time, so it carries no safety stock
    assert ss.loc["s1", "annual_carrying_usd"] == 0
    assert ss.loc["s3", "carrying_vs_best_usd"] > ss.loc["s2", "carrying_vs_best_usd"] > 0


def test_single_vs_dual_source_prices_the_trade_off(res):
    st = res.strategy.set_index("strategy")
    single = st.loc["single source"]
    dual = st.loc["dual source (50%/50%)"]
    t = res.tco.set_index("supplier")
    annual = res.usage.loc["B", "annual"]
    # expected value of supply at risk = P(disruption) x 2 weeks x 18 units x awarded landed price
    assert single["expected_exposure_usd"] == pytest.approx(0.1 * 2 * 18 * 13.2)
    assert dual["expected_exposure_usd"] == pytest.approx((0.1 * 0.5 + 0.9 * 0.5) * 2 * 18 * 13.2)
    assert dual["exposure_delta_usd"] > 0                 # the second source is riskier, not safer
    assert single["annual_cost_usd"] == pytest.approx(annual * t.loc["s1", "tco_usd_per_uom"])
    assert dual["cost_delta_usd"] == pytest.approx(annual * 0.5 * (t.loc["s2", "tco_usd_per_uom"] - t.loc["s1", "tco_usd_per_uom"]))
    assert np.isnan(dual["cost_per_usd_exposure_removed"])  # nothing was removed
    assert dual["awarded_risk_tier"] == "low" and dual["second_risk_tier"] == "high"


def test_strategy_note_explains_a_riskier_second_source(res):
    note = res.strategy_notes[0]
    assert "RAISES expected exposure" in note and "high risk against low" in note
    assert "stay single source" in note


def test_forward_buy_passes_the_index_move_through_at_the_material_share(res, sourcing_cfg):
    scen = pd.DataFrame(
        {"base": [100.0], "low_p10": [80.0], "median_p50": [100.0], "high_p90": [130.0]}, index=["B"]
    )
    fb = perf.forward_buy(sourcing_cfg, res.awards, res.should_cost, res.usage, scen).set_index("scenario")
    # material is 10.00 of the 13.20 quote, so a +30% index move adds 3.00
    assert fb.loc["high_p90", "spot_usd_per_uom"] == pytest.approx(16.2)
    assert fb.loc["median_p50", "spot_usd_per_uom"] == pytest.approx(13.2)
    assert fb.loc["low_p10", "spot_usd_per_uom"] == pytest.approx(11.2)
    # carrying 13.20 x 20%/yr for 4 of 52 weeks on average half the stock
    assert fb.loc["high_p90", "carrying_usd_per_uom"] == pytest.approx(13.2 * 0.2 * (4 / 52) / 2)
    assert fb.loc["high_p90", "forward_usd_per_uom"] == pytest.approx(13.2 + 0.1015384, abs=1e-6)
    assert fb["qty"].unique().tolist() == [4 * 18]
    assert fb["forward_wins"].tolist() == [False, False, True]   # p10, p50, p90 order
    assert fb.loc["high_p90", "saving_usd"] == pytest.approx((16.2 - fb.loc["high_p90", "forward_usd_per_uom"]) * 72)


def test_forward_buy_needs_a_price_index(res, sourcing_cfg):
    assert perf.forward_buy(sourcing_cfg, res.awards, res.should_cost, res.usage, None).empty
    assert perf.forward_buy(sourcing_cfg, res.awards, res.should_cost, res.usage, pd.DataFrame()).empty


def test_blg_forward_buy_only_covers_items_with_a_linked_series():
    r = run("products/blg_whey_protein.yaml", offline=True)
    assert set(r.forward_buy["item"]) == {"GLUCOSE"}       # the only priced item in the base BOM
    assert (r.forward_buy["breakeven_usd_per_uom"] > r.forward_buy["carrying_usd_per_uom"]).all()


def test_reorder_levels_by_hand():
    from conftest import BLG
    from ppsim.pipeline import run
    res = run(BLG, fetch_prices=False)
    lv = perf.reorder_levels(res.cfg, res.quotes, res.awards, res.usage)
    z, cv = res.cfg.sourcing.service_level_z, res.cfg.demand.noise_cv
    r = lv.loc["NH3"]
    d, L, sl = r["weekly_usage"], r["lead_time_weeks"], r["lead_time_sigma"]
    ss = z * math.sqrt(L * (cv * d) ** 2 + (d * sl) ** 2)
    assert math.isclose(r["safety_stock"], ss)
    assert r["min_qty"] == math.ceil(d * L + ss)                         # whole kg
    assert r["max_qty"] == r["min_qty"] + r["order_qty"]
    g = lv.loc["GLUCOSE"]
    assert g["safety_stock"] >= res.cfg.items["GLUCOSE"].planning.safety_stock   # plan's floor kept
    assert g["order_qty"] % 250000 == 0 and g["min_qty"] % 25000 == 0     # fixed lot, whole tankers
    m = lv.loc["UFDF-MEMBRANE-SET"]
    assert m["min_qty"] >= 1 and m["order_qty"] == 1 and float(m["min_qty"]).is_integer()
