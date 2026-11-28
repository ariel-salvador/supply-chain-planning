"""MOCK operating history (ADR 0018): hand-checkable rules on the weekly ledger.

Offline: prices are a flat synthetic series, so standards and PPV are checkable by hand.
"""
import math

import numpy as np
import pandas as pd
import pytest
import yaml

from conftest import BLG
from ppsim import history as H
from ppsim.config import ConfigError, load_config
from ppsim.pipeline import run

CORN, SUGAR = 200.0, 20.0  # flat USD/t corn and US cents/lb sugar


@pytest.fixture(scope="module")
def case():
    res = run(BLG, fetch_prices=False)
    cfg = res.cfg
    idx = pd.date_range("2020-01-01", "2026-07-01", freq="MS")
    from ppsim.feedstock import item_prices
    prices = item_prices(cfg, {"PMAIZMTUSDM": pd.Series(CORN, index=idx), "PSUGAISAUSDM": pd.Series(SUGAR, index=idx)})
    hist = H.simulate(cfg, prices, res.quotes, res.awards)
    return cfg, prices, res, hist


def test_every_item_balances_every_week_and_never_goes_negative(case):
    _, _, _, hist = case
    assert H.conservation_errors(hist) == []
    assert (hist.flows["closing"] >= -1e-6).all()
    # the weekly flows chain: this week's opening is last week's closing
    for item, g in hist.flows.groupby("item"):
        assert np.allclose(g["opening"].to_numpy()[1:], g["closing"].to_numpy()[:-1])


def test_deterministic(case):
    cfg, prices, res, hist = case
    again = H.simulate(cfg, prices, res.quotes, res.awards)
    assert hist.sales["qty"].equals(again.sales["qty"]) and hist.purchases["key"].equals(again.purchases["key"])


def test_window_is_whole_weeks_ending_by_end(case):
    cfg, _, _, hist = case
    assert hist.weeks[0] == pd.Timestamp("2024-01-01") and all(w.weekday() == 0 for w in hist.weeks)
    assert hist.end <= pd.Timestamp(cfg.history.end) and hist.end.weekday() == 6
    assert H.mondays("2024-01-03", "2024-01-20").tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-08")]


def test_whole_batches_within_fermenter_capacity(case):
    cfg, _, _, hist = case
    cap, rate = H.max_batches_per_week(cfg, "BLG-FERM", 12000.0)
    assert cap == 3 and math.isclose(rate, 3 * 168 * 0.96 / 144)     # 3 reactors, 96% uptime, 144 h cycle
    assert hist.kpis["batches_started"].max() <= cap
    ferm = hist.production[hist.production["product"] == "BLG-FERM"]
    assert (ferm["qty"] == 12000.0).all()


def test_demand_grows_into_the_plan_base(case):
    cfg, _, _, hist = case
    k = hist.kpis
    first, last = k["forecast"].iloc[:52].mean(), k["forecast"].iloc[-52:].mean()
    assert 0.6 * cfg.demand.base_per_period < first < 0.75 * cfg.demand.base_per_period   # ~30,000 / 1.15^3
    assert last / first > 1.25


def test_orders_ship_in_whole_bags(case):
    _, _, _, hist = case
    assert np.allclose(hist.sales["qty"] % 25, 0) or np.allclose((hist.sales["qty"] % 25) - 25, 0)


def test_nothing_in_the_past_stays_open(case):
    _, _, _, hist = case
    end = hist.end + pd.Timedelta(hours=12)
    s = hist.sales
    past_due = s[s["date_promised"] <= end]
    open_late = past_due[past_due["date_shipped"].isna()]
    # every order due by the end shipped, except one held in the very last week (ships next week)
    assert (open_late["hold"] & (open_late["due_week"] == len(hist.weeks) - 1)).all()
    shipped = s[s["date_shipped"].notna()]
    assert (shipped["date_shipped"] <= end).all() and shipped["invoice_date"].notna().all()
    assert (s["date_paid"].dropna() <= end).all()
    p = hist.purchases
    assert (p["date_order"] <= end).all()
    received = p[p["date_received"].notna()]
    assert (received["date_received"] <= end).all() and received["bill_date"].notna().all()
    late_open = p[p["date_received"].isna()]
    assert (late_open["date_promised"] + pd.Timedelta(weeks=8) > end).all()   # only recent orders are still open


def test_open_receivables_are_recent_or_from_slow_payers(case):
    cfg, _, _, hist = case
    open_ar = hist.sales[hist.sales["invoice_date"].notna() & hist.sales["date_paid"].isna()]
    assert len(open_ar) > 0                                              # something to age
    age = (hist.end - open_ar["invoice_date"]).dt.days
    slow = {c for c, p in cfg.history.customers.items() if p.pay_days > 45}
    assert ((age <= 60) | open_ar["customer"].isin(slow)).all()


def test_standard_cost_and_selling_price_by_hand(case):
    cfg, prices, res, hist = case
    std = hist.standards.set_index(["year", "item"])["std_usd_per_uom"]
    # glucose: corn USD/t / 1000 x corn per glucose -> material; + 22% conversion; + 12% margin; x awarded index
    material = CORN / 1000 * cfg.derived["corn_kg_per_glucose_kg"]
    target = material * 1.22 * 1.12
    idx = cfg.suppliers[res.awards.loc["GLUCOSE", "awarded_to"]].quote.price_index
    assert math.isclose(std[(2025, "GLUCOSE")], target * idx, rel_tol=1e-9)
    assert math.isclose(std[(2025, "BLG-PWD")], std[(2025, "BLG-PWD:material")] + 7.50)
    # list price: reset quarterly from the prior month's cost, grossed up by the 30% margin
    pl = hist.price_list
    assert (pl["valid_from"].dt.month.isin([1, 4, 7, 10])).all()
    assert np.allclose(pl["list_price"], (pl["cost_basis"] / 0.7).round(2))
    assert 12 < pl["list_price"].mean() < 16                             # ~USD 14/kg
    jan = pl[pl["valid_from"] == "2025-01-01"].iloc[0]
    assert math.isclose(jan["cost_basis"], std[(2025, "BLG-PWD")])       # January list = new standard
    # flat prices: an indexed item has no PPV at the awarded supplier
    glu = hist.purchases[(hist.purchases["item"] == "GLUCOSE") & ~hist.purchases["emergency"]]
    assert (glu["ppv_usd"].abs() <= glu["qty_received"] * 0.5e-4 + 1e-9).all()   # only 4-decimal price rounding


def test_contamination_scraps_one_batch_on_or_after_its_week(case):
    cfg, _, _, hist = case
    ev = next(e for e in cfg.history.events if e.kind == "contamination")
    lost = hist.production[hist.production["scrapped"]]
    assert len(lost) == 1 and lost["date_start"].iloc[0] >= pd.Timestamp(ev.start)
    assert hist.flows["scrapped"].sum() == 12000.0


def test_outage_moves_buying_to_the_runner_up(case):
    cfg, _, res, hist = case
    ev = next(e for e in cfg.history.events if e.kind == "supplier_outage")
    a = pd.Timestamp(ev.start)
    b = a + pd.Timedelta(weeks=ev.weeks)
    p = hist.purchases
    inc = p[(p["supplier"] == ev.target) & p["date_received"].notna()]
    assert not ((inc["date_received"] >= a) & (inc["date_received"] < b)).any()   # nothing arrives from it
    em = p[p["emergency"]]
    assert len(em) >= 1 and (em["date_order"] >= a).all() and (em["date_order"] < b).all()
    runner = res.quotes[(res.quotes["item"] == ev.item) & (res.quotes["rank"] == 2)]["supplier"].iloc[0]
    assert set(em["supplier"]) == {runner}
    assert (em["ppv_usd"] > 0).all()                                     # the premium supplier costs more


def test_spike_orders_are_flagged_and_unforecast(case):
    cfg, _, _, hist = case
    ev = next(e for e in cfg.history.events if e.kind == "demand_spike")
    spiked = hist.sales[hist.sales["spike"]]
    assert len(spiked) == ev.weeks and set(spiked["customer"]) == {ev.target}
    k = hist.kpis.set_index("week")
    a = pd.Timestamp(ev.start)
    window = k.loc[a:a + pd.Timedelta(weeks=ev.weeks - 1)]
    assert (window["demand"] > window["forecast"]).mean() > 0.6


def _raw():
    return yaml.safe_load(BLG.read_text())


def test_history_config_is_validated(tmp_path):
    raw = _raw()
    raw["history"]["customers"]["c_brands"]["share"] = "mock_cust_share_beverage"   # shares no longer sum to 1
    p = tmp_path / "x.yaml"
    raw["registry"] = str(BLG.parent / raw["registry"])
    p.write_text(yaml.safe_dump(raw, sort_keys=False))
    with pytest.raises(ConfigError, match="sum to 1"):
        load_config(p)
    raw = _raw()
    raw["registry"] = str(BLG.parent / raw["registry"])
    raw["history"]["events"][0]["start"] = "2030-01-01"
    p.write_text(yaml.safe_dump(raw, sort_keys=False))
    with pytest.raises(ConfigError, match="outside the history window"):
        load_config(p)


def test_customers_pay_list_less_their_discount(case):
    cfg, _, _, hist = case
    s = hist.sales
    for cid, p in cfg.history.customers.items():
        rows = s[s["customer"] == cid]
        assert np.allclose(rows["price_unit"], (rows["list_price"] * (1 - p.discount)).round(2))
    assert s.groupby("customer")["price_unit"].mean()["c_distributor"] < s["list_price"].mean()


def test_mock_bases_move_with_their_cited_index():
    from ppsim.feedstock import indexed_prices
    cfg = load_config(BLG)
    sid = cfg.sourcing.material_index["NH3"]
    idx = pd.date_range("2025-01-01", periods=24, freq="MS")
    series = pd.Series(100.0, index=idx)
    series[idx >= "2026-06-01"] = 150.0                                  # a 50% index rise
    out = indexed_prices(cfg, {sid: series})
    base = cfg.sourcing.material_base["NH3"]
    assert math.isclose(out.loc["2026-01-01", "NH3"], base)              # level = mock base at the base month
    assert math.isclose(out.loc["2026-07-01", "NH3"], base * 1.5)        # movement = the index
    assert set(out.columns) == {"NH3", "AMSULF"}                         # only items on that series


def test_rush_orders_are_placed_one_week_ahead_and_spike_volume_is_rush(case):
    cfg, _, _, hist = case
    s = hist.sales
    lead = cfg.history.order_lead_weeks
    weeks_ahead = s["due_week"] - s["placed_week"]
    assert set(weeks_ahead[s["rush"]]) == {1} and set(weeks_ahead[~s["rush"]]) == {lead}
    assert s.loc[s["spike"], "rush"].all()
    assert 0.03 < s["rush"].mean() < 0.25


def test_held_shipments_ship_one_week_late_and_otif_is_believable(case):
    _, _, _, hist = case
    s = hist.sales[hist.sales["date_shipped"].notna()]
    held = s[s["hold"]]
    assert len(held) > 0 and (held["ship_week"] >= held["due_week"] + 1).all()
    otif = (s["ship_week"] == s["due_week"]).mean()
    assert 0.93 < otif < 0.99


def test_contamination_takes_a_fermenter_and_the_powder_line_offline(case):
    cfg, _, _, hist = case
    ev = next(e for e in cfg.history.events if e.kind == "contamination")
    k = hist.kpis.set_index("week")
    a = pd.Timestamp(ev.start)
    down = k.loc[a:a + pd.Timedelta(weeks=ev.weeks - 1)]
    assert (down["batch_capacity"] < k["batch_capacity"].max()).all()      # one fermenter of three offline
    assert (down["batches_started"] <= 2).all()
    pwd = hist.production[hist.production["product"] == "BLG-PWD"]
    sanitised = a + pd.Timedelta(weeks=1)
    assert not ((pwd["date_start"] >= sanitised) & (pwd["date_start"] < sanitised + pd.Timedelta(weeks=1))).any()
