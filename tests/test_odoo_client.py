import importlib.util

import pytest

from conftest import ROOT

spec = importlib.util.spec_from_file_location("odoo_client", ROOT / "scripts" / "odoo_client.py")
oc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oc)


class FakeOdoo(oc.Odoo):
    """In-memory stand-in for the JSON-2 API: just enough for ensure()."""

    def __init__(self):
        self.key, self.db, self.url, self.refs = "k", "pps_live", "http://x", {}
        self.rows = {}  # model -> list of dicts
        self.writes = []

    def call(self, model, method, ids=(), **params):
        rows = self.rows.setdefault(model, [])
        if method == "search_read":
            (field, _, value), = params["domain"]
            hits = [r for r in rows if r.get(field) == value]
            return [{"id": r["id"]} for r in hits][: params.get("limit") or None]
        if method == "create":
            vals = params["vals_list"][0]
            rows.append({"id": len(rows) + 1, **vals})
            return [len(rows)]
        if method == "write":
            self.writes.append((model, ids, params))
            return True
        raise AssertionError(f"unexpected call {model}.{method}")


def test_ensure_creates_once_then_skips():
    o = FakeOdoo()
    rid, created = o.ensure("sale.order", "so_2025w14_c_brands", {"partner_id": 7})
    assert created and rid == 1
    rid2, created2 = o.ensure("sale.order", "so_2025w14_c_brands", {"partner_id": 999})
    assert (rid2, created2) == (1, False)
    assert len(o.rows["sale.order"]) == 1
    assert o.rows["sale.order"][0]["partner_id"] == 7      # rerun did not overwrite
    assert o.rows["sale.order"][0][oc.PPS_KEY] == "so_2025w14_c_brands"
    assert o.writes == []                                   # ensure never writes


def test_ensure_never_touches_manual_records():
    o = FakeOdoo()
    o.rows["purchase.order"] = [{"id": 1, "partner_id": 3}]  # created by hand: no key
    rid, created = o.ensure("purchase.order", "po_x", {"partner_id": 3})
    assert created and rid == 2
    assert o.rows["purchase.order"][0] == {"id": 1, "partner_id": 3}


def test_ensure_rejects_duplicate_keys_and_empty_key():
    o = FakeOdoo()
    o.rows["res.partner"] = [{"id": 1, oc.PPS_KEY: "dup"}, {"id": 2, oc.PPS_KEY: "dup"}]
    with pytest.raises(oc.OdooError, match="share"):
        o.ensure("res.partner", "dup", {})
    with pytest.raises(oc.OdooError, match="non-empty"):
        o.ensure("res.partner", "", {})


def test_pending_changes_shows_diff_without_applying():
    current = {"name": "Glucose", "uom_id": [16, "kg"], "list_price": 0.5, "sale_ok": False}
    desired = {"name": "Glucose (corn)", "uom_id": 16, "list_price": 0.5, "sale_ok": False}
    assert oc.pending_changes(current, desired) == {"name": ("Glucose", "Glucose (corn)")}
    assert oc.pending_changes(current, {"uom_id": 1}) == {"uom_id": (16, 1)}


def test_live_reads_refs_file(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "ROOT", tmp_path)
    (tmp_path / ".odoo-apikey-live").write_text("abc\n")
    (tmp_path / ".odoo-live-refs.json").write_text('{"uom.product_uom_kgm": 16}')
    o = oc.Odoo.live(url="http://x")
    assert o.db == "pps_live" and o.key == "abc"
    assert o.ref("uom.product_uom_kgm") == 16  # no API call needed


def test_pending_changes_ignores_odoo_rounding_but_not_real_edits():
    stored = {"product_qty": 13636.3636}                 # Odoo keeps 4 decimals
    assert oc.pending_changes(stored, {"product_qty": 13636.363636363636}, float_tol=0.5e-4) == {}
    assert oc.pending_changes(stored, {"product_qty": 13636.37}, float_tol=0.5e-4) != {}
    assert oc.pending_changes(stored, {"product_qty": 13636.363636363636}) != {}  # strict by default
