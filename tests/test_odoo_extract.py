import importlib.util
import sys

import pandas as pd
import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("odoo_extract", ROOT / "scripts" / "odoo_extract.py")
ox = importlib.util.module_from_spec(spec)
sys.modules["odoo_extract"] = ox
spec.loader.exec_module(ox)
import odoo_client as oc  # noqa: E402


def test_many2one_and_dates():
    assert ox.m2o_id([7, "Glucose"]) == 7 and ox.m2o_name([7, "Glucose"]) == "Glucose"
    assert ox.m2o_id(False) is None and ox.odoo_date(False) is None
    assert ox.week_start(pd.Timestamp("2026-11-27 12:00")) == pd.Timestamp("2026-11-23")  # Fri -> Mon
    assert ox.product_code("[BLG-PWD] rBLG protein powder") == "BLG-PWD"


def test_created_by_distinguishes_scripts_from_people():
    bot = {11}
    assert ox.created_by({"create_uid": [11, "PPS Bot"]}, bot, demo=False) == "script"
    assert ox.created_by({"create_uid": [2, "Admin"], oc.PPS_KEY: "so_1"}, bot, demo=False) == "script"
    assert ox.created_by({"create_uid": [2, "Admin"], oc.PPS_KEY: False}, bot, demo=False) == "manual"
    assert ox.created_by({"create_uid": [2, "Admin"]}, bot, demo=True) == "demo"


def test_lines_join_their_orders_and_flatten():
    orders = [{"id": 1, "name": "PO1", "date_order": "2026-11-23 08:00:00", "partner_id": [5, "Sugar Co"],
               "state": "purchase", "create_uid": [2, "Admin"]}]
    lines = [{"id": 10, "order_id": [1, "PO1"], "product_id": [3, "[GLUCOSE] Glucose"], "product_qty": 250000.0},
             {"id": 11, "order_id": [99, "orphan"], "product_id": [3, "x"], "product_qty": 1.0}]
    df = ox.lines_with_orders(lines, orders, {"product": "product_id", "qty_ordered": "product_qty"},
                              {"date_order": "date_order", "vendor": "partner_id", "state": "state"}, set(), False)
    df = ox.finish(df, ["date_order"], ["product", "vendor"], "date_order")
    assert len(df) == 1                                   # the orphan line is dropped
    row = df.iloc[0]
    assert row["product_code"] == "GLUCOSE" and row["vendor_name"] == "Sugar Co"
    assert row["week"] == pd.Timestamp("2026-11-23") and row["created_by"] == "manual"


def test_reader_client_refuses_writes_before_sending():
    r = oc.ReadOnlyOdoo.__new__(oc.ReadOnlyOdoo)          # no network, no key needed
    for call in (lambda: r.create("purchase.order", {}), lambda: r.write("product.product", [1], {}),
                 lambda: r.call("purchase.order", "button_confirm", ids=[1]), lambda: r.ensure("x", "k", {})):
        with pytest.raises(oc.OdooError, match="read-only"):
            call()


def test_write_produces_csv_and_duckdb(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    tables = {"fact_sales": pd.DataFrame({"qty": [1.0, 2.0]}), "fact_stock": pd.DataFrame()}
    target = ox.write(tables, "pps_test", tmp_path)
    assert (target / "fact_sales.csv").exists() and (target / "meta.csv").exists()
    con = duckdb.connect(str(target / "pps.duckdb"), read_only=True)
    assert con.execute("select sum(qty) from fact_sales").fetchone()[0] == 3.0
    assert con.execute("select rows_fact_sales from meta").fetchone()[0] == 2


@pytest.mark.parametrize("src,dst,kind,sign", [
    ("supplier", "internal", "receipt", 1),
    ("internal", "customer", "delivery", -1),
    ("production", "internal", "production", 1),
    ("internal", "production", "consumption", -1),
    ("internal", "inventory", "scrap/adjustment", -1),
    ("inventory", "internal", "scrap/adjustment", 1),
    ("internal", "internal", "internal", 0),
])
def test_stock_move_kind_and_on_hand_sign(src, dst, kind, sign):
    assert ox.move_kind(src, dst) == kind
    assert ox.on_hand_sign(src, dst) == sign
