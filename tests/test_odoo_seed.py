"""The sourcing part of the Odoo seed, tested offline (no Odoo instance needed).

`supplier_prices` and `rfq_lines` are pure: they turn the engine's RFQ result into the
payloads the seeder posts, so what Odoo would receive can be checked without Docker.
"""
import importlib.util

import pytest

from ppsim.pipeline import run
from conftest import BLG, ROOT

spec = importlib.util.spec_from_file_location("odoo_seed", ROOT / "scripts" / "odoo_seed.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


@pytest.fixture(scope="module")
def res():
    return run(BLG, fetch_prices=False)


@pytest.fixture(scope="module")
def purchased(res):
    from ppsim import bom as bom_mod

    planned = bom_mod.reachable(res.cfg.demand.item, res.cfg.bom)
    return [i for i in planned if res.cfg.items[i].type == "purchased"]


def test_every_bidder_gets_a_price_list_line_awarded_first(res, purchased):
    rows = seed.supplier_prices(res.cfg, res, 7.0, purchased)
    assert len(rows) == 3 * len(purchased)                       # three bidders per item
    for iid in purchased:
        item_rows = [r for r in rows if r[0] == iid]
        assert [v["sequence"] for _, _, v in item_rows] == [1, 2, 3]
        first_supplier = item_rows[0][1]
        assert first_supplier == res.awards.loc[iid, "awarded_to"]   # Odoo buys from sequence 1
        # price, minimum quantity and lead time come straight off the quote
        q = res.quotes[(res.quotes["item"] == iid) & (res.quotes["supplier"] == first_supplier)].iloc[0]
        vals = item_rows[0][2]
        assert vals["price"] == pytest.approx(q["quoted_usd_per_uom"], abs=1e-4)
        assert vals["min_qty"] == pytest.approx(q["moq_qty"], abs=1e-4)
        assert vals["delay"] == int(round(q["lead_time_weeks"] * 7))


def test_rfq_lines_group_by_supplier_at_the_volume_quoted(res, purchased):
    rfqs = seed.rfq_lines(res.cfg, res, purchased)
    assert set(rfqs) == set(res.quotes[res.quotes["item"].isin(purchased)]["supplier"])
    for sid, lines in rfqs.items():
        for iid, qty, price in lines:
            assert iid in purchased
            assert qty == pytest.approx(res.usage.loc[iid, "gross_requirements"], abs=1e-4)
            q = res.quotes[(res.quotes["item"] == iid) & (res.quotes["supplier"] == sid)].iloc[0]
            assert price == pytest.approx(q["quoted_usd_per_uom"], abs=1e-4)
    # the sucrose variant is not in the active BOM, so nobody is asked to quote it
    assert all(iid != "SUCROSE" for lines in rfqs.values() for iid, _, _ in lines)


def test_rfq_round_is_marked_so_it_is_never_read_as_a_plan():
    assert seed.RFQ_ORIGIN == "RFQ round [mock]"
    run_py = (ROOT / "scripts" / "odoo_run.py").read_text()
    compare_py = (ROOT / "scripts" / "compare_plans.py").read_text()
    assert 'RFQ_ORIGIN = "RFQ round [mock]"' in run_py and '"rfq"' in run_py
    assert '"rfq" in odoo.columns' in compare_py


def test_no_sourcing_config_falls_back_to_the_vendor_list(sourcing_cfg):
    from dataclasses import replace

    plain = replace(sourcing_cfg, suppliers={}, sourcing=None)
    r = run(plain, fetch_prices=False)
    assert r.quotes is None and r.awards is None
    assert seed.supplier_prices(plain, r, 7.0, ["B"]) == []
    assert seed.rfq_lines(plain, r, ["B"]) == {}
