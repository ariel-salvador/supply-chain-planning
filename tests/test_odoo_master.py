import importlib.util
import sys

import pytest

from conftest import BLG, ROOT

sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("odoo_master", ROOT / "scripts" / "odoo_master.py")
om = importlib.util.module_from_spec(spec)
sys.modules["odoo_master"] = om  # dataclasses (py3.9) look the module up while loading
spec.loader.exec_module(om)
import odoo_client as oc  # noqa: E402

from ppsim.config import load_config  # noqa: E402
from ppsim.pipeline import run  # noqa: E402


@pytest.fixture(scope="module")
def specs():
    cfg = load_config(BLG)
    return om.plan(cfg, run(cfg, fetch_prices=False), days_per_week=7)


class FakeOdoo(oc.Odoo):
    """In-memory JSON-2 stand-in: records per model, keyed lookups, variants, writes."""

    def __init__(self):
        self.key, self.db, self.url = "k", "pps_live", "http://x"
        self.refs = {x: i for i, x in enumerate([
            "uom.product_uom_kgm", "uom.product_uom_unit", "mrp.route_warehouse0_manufacture",
            "purchase_stock.route_warehouse0_buy", "stock.stock_location_stock"], start=100)}
        self.rows = {}
        self.writes = []

    def call(self, model, method, ids=(), **p):
        rows = self.rows.setdefault(model, [])
        if method == "search_read":
            (f, _, v), = p["domain"]
            hits = [r for r in rows if r.get(f) == v]
            return [{k: r.get(k) for k in ["id", *p["fields"]]} for r in hits][: p.get("limit") or None]
        if method == "create":
            vals = p["vals_list"][0]
            rows.append({"id": len(rows) + 1, **vals})
            if model == "product.template":  # Odoo creates the variant automatically
                pp = self.rows.setdefault("product.product", [])
                pp.append({"id": len(pp) + 1, "product_tmpl_id": len(rows)})
            return [len(rows)]
        if method == "write":
            for r in rows:
                if r["id"] in ids:
                    r.update(p["vals"])
            self.writes.append((model, list(ids), p["vals"]))
            return True
        raise AssertionError(f"unexpected {model}.{method}")


def test_plan_covers_the_master_data(specs):
    count = {}
    for s in specs:
        count[s.model] = count.get(s.model, 0) + 1
    assert count["product.template"] == 10
    assert count["mrp.bom"] == 2
    assert count["stock.warehouse.orderpoint"] == 10
    assert count["res.partner"] >= 5 + 4          # customers + at least one bidder per family
    assert count["uom.uom"] >= 2                  # fermentation batch + glucose lot
    keys = [s.key for s in specs]
    assert len(keys) == len(set(keys)), "every spec has a unique key"


def test_plan_orders_dependencies_first(specs):
    seen = set()
    for s in specs:
        for ref in _refs(s.vals):
            assert ref in seen, f"{s.key} refers to {ref} before it is planned"
        seen.add(s.key)


def test_reorder_rules_default_to_manual_trigger(specs):
    assert {s.vals["trigger"] for s in specs if s.model == "stock.warehouse.orderpoint"} == {"manual"}


def test_apply_is_idempotent_and_shows_diffs_without_applying(specs):
    o = FakeOdoo()
    first = om.apply(o, specs)
    assert len(first.created) == len(specs) and not first.diffs
    second = om.apply(o, specs)
    assert not second.created and not second.diffs and len(second.unchanged) == len(specs)
    # the user edits a reorder rule in the UI
    op = next(r for r in o.rows["stock.warehouse.orderpoint"] if r[oc.PPS_KEY] == "orderpoint:BLG-PWD")
    op["product_min_qty"] = 99999.0
    o.writes.clear()
    third = om.apply(o, specs)
    assert [d[0].key for d in third.diffs] == ["orderpoint:BLG-PWD"]
    assert op["product_min_qty"] == 99999.0 and o.writes == []      # shown, not applied
    fourth = om.apply(o, specs, apply_diffs=True)
    assert op["product_min_qty"] != 99999.0                         # applied only on request
    assert [m for m, _, _ in o.writes] == ["stock.warehouse.orderpoint"]


def _refs(value):
    if isinstance(value, om.Ref):
        yield value.key
    elif isinstance(value, om.Variant):
        yield value.template_key
    elif isinstance(value, dict):
        for v in value.values():
            yield from _refs(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _refs(v)


def test_kanban_levels_set_purchased_reorder_rules():
    import pandas as pd
    cfg = load_config(BLG)
    levels = pd.DataFrame({"min_qty": [928.0], "max_qty": [1613.0]}, index=["AMSULF"])
    specs = om.plan(cfg, run(cfg, fetch_prices=False), days_per_week=7, levels=levels)
    op = {s.key: s.vals for s in specs if s.model == "stock.warehouse.orderpoint"}
    assert (op["orderpoint:AMSULF"]["product_min_qty"], op["orderpoint:AMSULF"]["product_max_qty"]) == (928.0, 1613.0)
    ss = cfg.items["BLG-PWD"].planning.safety_stock
    assert op["orderpoint:BLG-PWD"]["product_min_qty"] == op["orderpoint:BLG-PWD"]["product_max_qty"] == ss
