"""Sourcing: should-cost, RFQ scoring, award and TCO.

Every expectation is computed by hand in the comments. Fixture (conftest):
item B should-cost = 10 material + 20% conversion (2.00) + 10% margin (1.20) = 13.20;
bidders s1/s2/s3 quote 1.0x / 0.8x / 1.2x of it = 13.20 / 10.56 / 15.84.
"""
import numpy as np
import pandas as pd
import pytest

from ppsim import sourcing as src
from ppsim.config import ConfigError, parse_config
from ppsim.pipeline import run
from conftest import BLG


@pytest.fixture
def pieces(sourcing_cfg):
    """should-cost, usage and scored quotes for the fixture config."""
    res = run(sourcing_cfg, fetch_prices=False)
    return res


# --- helpers ---------------------------------------------------------------


@pytest.mark.parametrize("freq,expected", [("W-SUN", 52), ("W", 52), ("MS", 12), ("M", 12), ("D", 365)])
def test_periods_per_year(freq, expected):
    assert src.periods_per_year(freq) == expected


def test_periods_per_year_rejects_unknown():
    with pytest.raises(ValueError, match="annualising"):
        src.periods_per_year("Y")


def test_range_score_puts_best_at_one_and_worst_at_zero():
    x = pd.Series([2.0, 4.0, 6.0])
    assert src.range_score(x, lower_is_better=True).tolist() == [1.0, 0.5, 0.0]
    assert src.range_score(x, lower_is_better=False).tolist() == [0.0, 0.5, 1.0]
    # a criterion every bid ties on cannot separate them: all score 1
    assert src.range_score(pd.Series([3.0, 3.0]), True).tolist() == [1.0, 1.0]


# --- M6a/M6c: usage and should-cost ---------------------------------------


def test_planned_usage_only_counts_purchased_items(pieces):
    u = pieces.usage
    assert list(u.index) == ["B"]                      # A is finished, not purchased
    # demand 10/period x 5 periods - 5 on hand = 45 units of A, 2 of B per A = 90
    assert u.loc["B", "gross_requirements"] == pytest.approx(90.0)
    assert u.loc["B", "per_bucket"] == pytest.approx(18.0)   # 90 / 5 buckets
    assert u.loc["B", "annual"] == pytest.approx(18.0 * 52)  # weekly buckets


def test_should_cost_build_up_and_material_share(pieces):
    sc = pieces.should_cost.loc["B"]
    assert sc["material_usd"] == 10 and sc["material_basis"] == "mock base"
    assert sc["conversion_usd"] == pytest.approx(2.0)
    assert sc["margin_usd"] == pytest.approx(1.2)       # 10% of (10 + 2)
    assert sc["target_price_usd"] == pytest.approx(13.2)
    assert sc["material_share"] == pytest.approx(10 / 13.2)


def test_should_cost_prefers_a_linked_price_index(sourcing_cfg):
    sc = src.should_cost(sourcing_cfg, {"B": 20.0})
    assert sc.loc["B", "material_usd"] == 20.0
    assert sc.loc["B", "target_price_usd"] == pytest.approx(20 * 1.2 * 1.1)
    assert "index" in sc.loc["B", "material_basis"]


def test_blg_should_cost_uses_the_cited_corn_index_when_prices_are_available():
    res = run(BLG, offline=True)
    basis = res.should_cost.loc["GLUCOSE", "material_basis"]
    assert basis == "cited index PMAIZMTUSDM"
    # items with no linked series fall back to a labelled mock base
    assert res.should_cost.loc["NH3", "material_basis"] == "mock base"


# --- M6b: quotes, scoring, award -----------------------------------------


def test_quote_table_terms(pieces):
    q = pieces.quotes.set_index("supplier")
    assert q.loc["s1", "quoted_usd_per_uom"] == pytest.approx(13.2)
    assert q.loc["s2", "quoted_usd_per_uom"] == pytest.approx(10.56)
    assert q.loc["s3", "quoted_usd_per_uom"] == pytest.approx(15.84)
    # lead time = the item's planning lead time (1) + the quoted delta (0 / 1 / 2)
    assert q.loc[["s1", "s2", "s3"], "lead_time_weeks"].tolist() == [1, 2, 3]
    # MOQ = quoted weeks of cover x planned usage per bucket (18)
    assert q.loc[["s1", "s2", "s3"], "moq_qty"].tolist() == [18.0, 36.0, 72.0]
    # the negotiation gap against should-cost
    assert q.loc["s2", "gap_usd"] == pytest.approx(10.56 - 13.2)
    assert q.loc["s2", "gap_pct"] == pytest.approx(-0.2)


def test_quoted_lead_time_floors_at_one_bucket(sourcing_raw, sourcing_registry):
    sourcing_registry["lt1"] = type(sourcing_registry["lt1"])(
        **{**sourcing_registry["lt1"].__dict__, "value": -5.0}
    )
    cfg = parse_config(sourcing_raw, sourcing_registry)
    res = run(cfg, fetch_prices=False)
    assert res.quotes.set_index("supplier").loc["s1", "lead_time_weeks"] == 1


def test_scores_and_weighted_total(pieces):
    q = pieces.quotes.set_index("supplier")
    # price 13.20 / 10.56 / 15.84 -> (max - x) / (max - min)
    assert q["price_score"].round(4).to_dict() == {"s1": 0.5, "s2": 1.0, "s3": 0.0}
    assert q["lead_time_score"].to_dict() == {"s1": 1.0, "s2": 0.5, "s3": 0.0}       # 1 / 2 / 3 weeks
    assert q["quality_score"].round(4).to_dict() == {"s1": 0.6667, "s2": 0.0, "s3": 1.0}  # 1000 / 2000 / 500 ppm
    assert q["risk_score_norm"].to_dict() == {"s1": 1.0, "s2": 0.0, "s3": 0.5}       # 0.9 / 0.1 / 0.5
    # weights price .5, lead time .2, quality .2, risk .1
    assert q.loc["s1", "total_score"] == pytest.approx(0.5 * 0.5 + 0.2 * 1 + 0.2 * (2 / 3) + 0.1 * 1)
    assert q.loc["s2", "total_score"] == pytest.approx(0.6)
    assert q.loc["s3", "total_score"] == pytest.approx(0.25)
    assert q["rank"].to_dict() == {"s1": 1, "s2": 2, "s3": 3}


def test_award_picks_the_best_total_not_the_lowest_price(pieces):
    aw = pieces.awards.loc["B"]
    assert aw["awarded_to"] == "s1" and aw["runner_up"] == "s2"
    assert aw["bids"] == 3
    assert aw["score_margin"] == pytest.approx(0.68333 - 0.6, abs=1e-4)
    assert aw["lowest_bid"] == "s2"
    assert aw["premium_vs_lowest_pct"] == pytest.approx(13.2 / 10.56 - 1)   # +25%
    assert aw["gap_vs_should_cost_pct"] == pytest.approx(0.0)


def test_award_rationale_names_the_decisive_criterion(pieces):
    r = pieces.awards.loc["B", "rationale"]
    # weighted score gaps vs the runner-up: price -.25, lead time +.10, quality +.133, risk +.10
    assert r.startswith("Awarded to One (fictional)")
    assert "Quality decided it at weight 20%" in r
    assert "1,000 ppm vs 2,000 ppm" in r
    assert "The lowest bid (Two (fictional)" in r
    assert "against should-cost" in r


def test_single_bid_rationale_says_so(sourcing_raw, sourcing_registry):
    raw = dict(sourcing_raw)
    raw["suppliers"] = [sourcing_raw["suppliers"][0]]
    res = run(parse_config(raw, sourcing_registry), fetch_prices=False)
    assert res.awards.loc["B", "bids"] == 1
    assert "Single bid" in res.awards.loc["B", "rationale"]
    assert np.isnan(res.awards.loc["B", "score_margin"])
    assert any("only 1 bid" in n for n in res.sourcing_notes)


# --- M6d: total cost of ownership ----------------------------------------


def test_tco_follows_the_incoterm(pieces):
    t = pieces.tco.set_index("supplier")
    # s1 DAP on a domestic lane: seller delivers, domestic duty is 0
    assert t.loc["s1", "freight_usd"] == 0 and t.loc["s1", "duty_usd"] == 0
    assert t.loc["s1", "landed_usd"] == pytest.approx(13.2)
    # s2 FOB on an import lane: the buyer pays 10% freight, then 5% duty on the sum
    assert t.loc["s2", "freight_usd"] == pytest.approx(1.056)
    assert t.loc["s2", "duty_usd"] == pytest.approx((10.56 + 1.056) * 0.05)
    assert t.loc["s2", "landed_usd"] == pytest.approx(10.56 + 1.056 + 0.5808)
    # s3 DDP: the seller pays both, so the quote is already landed
    assert t.loc["s3", "freight_usd"] == 0 and t.loc["s3", "duty_usd"] == 0
    assert t.loc["s3", "landed_usd"] == pytest.approx(15.84)


def test_tco_adds_moq_carrying_and_quality_cost(pieces):
    t = pieces.tco.set_index("supplier")
    # carrying = (MOQ / 2) x landed x 20% / annual volume; quality = landed x ppm x 2
    assert t.loc["s1", "moq_carrying_usd"] == pytest.approx(9 * 13.2 * 0.2 / (18 * 52))
    assert t.loc["s1", "quality_cost_usd"] == pytest.approx(13.2 * 1000 / 1e6 * 2)
    assert t.loc["s1", "tco_usd_per_uom"] == pytest.approx(
        13.2 + 9 * 13.2 * 0.2 / (18 * 52) + 13.2 * 0.002
    )
    assert t.loc["s1", "annual_tco_usd"] == pytest.approx(t.loc["s1", "tco_usd_per_uom"] * 18 * 52)


def test_tco_narrows_the_price_gap(pieces):
    """The cheap import bid keeps the lead here, but most of its discount is eaten."""
    t = pieces.tco.set_index("supplier")
    assert t.loc["s2", "price_rank"] == 1 and t.loc["s2", "tco_rank"] == 1
    price_gap = t.loc["s1", "unit_price_usd"] - t.loc["s2", "unit_price_usd"]
    tco_gap = t.loc["s1", "tco_usd_per_uom"] - t.loc["s2", "tco_usd_per_uom"]
    assert price_gap == pytest.approx(2.64)                    # 13.20 - 10.56
    assert tco_gap < price_gap / 2                             # freight, duty, MOQ and quality close it
    assert not pieces.tco_notes                                # same supplier wins on both measures


def test_tco_flags_items_where_the_cheapest_price_is_not_the_cheapest_cost():
    res = run(BLG, fetch_prices=False)
    t = res.tco.set_index(["item", "supplier"])
    # the cheap import bid for glucose carries freight, duty, a 6-week MOQ and 4,500 ppm
    assert t.loc[("GLUCOSE", "s_sugar_b"), "price_rank"] == 1
    assert t.loc[("GLUCOSE", "s_sugar_b"), "tco_rank"] > 1
    assert any(n.startswith("GLUCOSE: lowest price is") for n in res.tco_notes)


def test_awarded_supplier_gets_the_purchase_orders(pieces):
    assert src.awarded_vendor_map(pieces.awards, pieces.cfg) == {"B": ("s1", "One (fictional)")}
    assert set(pieces.po_lines["vendor_id"]) == {"s1"}


# --- loader validation ----------------------------------------------------


def test_weights_must_sum_to_one(sourcing_raw, sourcing_registry):
    sourcing_raw["sourcing"]["weights"]["price"] = "w_risk"
    with pytest.raises(ConfigError, match="sum to 1"):
        parse_config(sourcing_raw, sourcing_registry)


def test_weight_keys_are_fixed(sourcing_raw, sourcing_registry):
    sourcing_raw["sourcing"]["weights"]["delivery"] = "w_risk"
    with pytest.raises(ConfigError, match="keys must be exactly"):
        parse_config(sourcing_raw, sourcing_registry)


def test_supplier_must_be_fictional(sourcing_raw, sourcing_registry):
    sourcing_raw["suppliers"][0].pop("fictional")
    with pytest.raises(ConfigError, match="fictional"):
        parse_config(sourcing_raw, sourcing_registry)


def test_supplier_must_quote_a_purchased_item(sourcing_raw, sourcing_registry):
    sourcing_raw["suppliers"][0]["supplies"] = ["A"]
    with pytest.raises(ConfigError, match="not a purchased item"):
        parse_config(sourcing_raw, sourcing_registry)


def test_unknown_lane_and_incoterm_and_risk_tier(sourcing_raw, sourcing_registry):
    import copy

    bad_lane = copy.deepcopy(sourcing_raw)
    bad_lane["suppliers"][0]["lane"] = "air"
    with pytest.raises(ConfigError, match="unknown lane"):
        parse_config(bad_lane, sourcing_registry)
    bad_inco = copy.deepcopy(sourcing_raw)
    bad_inco["suppliers"][0]["incoterm"] = "XYZ"
    with pytest.raises(ConfigError, match="unknown incoterm"):
        parse_config(bad_inco, sourcing_registry)
    bad_risk = copy.deepcopy(sourcing_raw)
    bad_risk["suppliers"][0]["risk_tier"] = "extreme"
    with pytest.raises(ConfigError, match="unknown risk_tier"):
        parse_config(bad_risk, sourcing_registry)


def test_quoted_item_needs_a_should_cost_base(sourcing_raw, sourcing_registry):
    sourcing_raw["sourcing"]["should_cost"]["material_base"] = {}
    with pytest.raises(ConfigError, match="missing a base cost"):
        parse_config(sourcing_raw, sourcing_registry)


def test_suppliers_and_sourcing_come_together(sourcing_raw, sourcing_registry):
    import copy

    no_policy = copy.deepcopy(sourcing_raw)
    no_policy.pop("sourcing")
    with pytest.raises(ConfigError, match="needs a sourcing block"):
        parse_config(no_policy, sourcing_registry)
    no_suppliers = copy.deepcopy(sourcing_raw)
    no_suppliers.pop("suppliers")
    with pytest.raises(ConfigError, match="needs a suppliers block"):
        parse_config(no_suppliers, sourcing_registry)


def test_blg_supplier_master_is_complete_and_fictional():
    res = run(BLG, fetch_prices=False)
    cfg = res.cfg
    assert all("fictional" in s.name for s in cfg.suppliers.values())
    purchased_in_bom = {b.component for b in cfg.bom if cfg.items[b.component].type == "purchased"}
    quoted = {i for s in cfg.suppliers.values() for i in s.supplies}
    assert purchased_in_bom <= quoted                      # nothing bought without an RFQ
    assert (res.awards["bids"] >= 2).all()                 # every item has a competitive quote
