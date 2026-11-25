"""Extract Odoo into tidy tables (marts) for the dashboards. Read-only.

    .venv/bin/python scripts/odoo_extract.py                 # pps_live as pps-reader (default)
    .venv/bin/python scripts/odoo_extract.py --source demo   # pps_demo (read-only client)

Writes ``outputs/marts/<database>/``: one CSV per table (Tableau) and ``pps.duckdb``
with the same tables (Evidence). ``outputs/`` is gitignored: the marts are rebuilt from
Odoo on demand ("refresh on command"); every table carries the extraction timestamp
in ``meta``.

Tables
- ``dim_product``, ``dim_partner``: master data
- ``fact_sales``: sales order lines with their order's dates, customer and state
- ``fact_purchases``: purchase order lines with order dates, vendor and state
- ``fact_production``: manufacturing orders
- ``fact_stock``: on-hand quantity per product and internal location (snapshot)
- ``fact_reorder``: reorder rules with Odoo's forecast and suggested order quantity
- ``meta``: when, from which database, row counts

Every document row says who made it: ``created_by`` = ``script`` (pps-bot or a
``x_pps_key``), ``manual`` (someone in the UI) or ``demo`` (the disposable demo database).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import PPS_KEY, Odoo, OdooError, ReadOnlyOdoo  # noqa: E402

OUT = ROOT / "outputs" / "marts"


# ---------------------------------------------------------------------------
# pure helpers (unit-tested)
# ---------------------------------------------------------------------------


def m2o_id(v: Any) -> Optional[int]:
    return v[0] if isinstance(v, (list, tuple)) and v else None


def m2o_name(v: Any) -> Optional[str]:
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else None


def odoo_date(v: Any) -> Optional[pd.Timestamp]:
    """Odoo sends False for empty dates and 'YYYY-MM-DD[ HH:MM:SS]' strings otherwise."""
    return pd.Timestamp(v) if v else None


def week_start(ts: Optional[pd.Timestamp]) -> Optional[pd.Timestamp]:
    """Monday of the ISO week, the bucket the planning engine uses."""
    if ts is None or pd.isna(ts):
        return None
    d = ts.normalize()
    return d - pd.Timedelta(days=d.weekday())


def created_by(rec: Dict[str, Any], script_uids: set, demo: bool) -> str:
    if demo:
        return "demo"
    if rec.get(PPS_KEY) or m2o_id(rec.get("create_uid")) in script_uids:
        return "script"
    return "manual"


def product_code(name: Optional[str]) -> Optional[str]:
    """'[BLG-PWD] rBLG protein powder' -> 'BLG-PWD'."""
    if name and name.startswith("[") and "]" in name:
        return name[1 : name.index("]")]
    return name


def lines_with_orders(lines: List[dict], orders: List[dict], line_map: Dict[str, str],
                      order_map: Dict[str, str], script_uids: set, demo: bool) -> pd.DataFrame:
    """Join order lines to their orders and flatten many2one fields."""
    by_id = {o["id"]: o for o in orders}
    rows = []
    for ln in lines:
        order = by_id.get(m2o_id(ln.get("order_id")))
        if order is None:
            continue
        row = {"line_id": ln["id"], "order_id": order["id"], "order_ref": order.get("name")}
        for out, src in order_map.items():
            row[out] = order.get(src)
        for out, src in line_map.items():
            row[out] = ln.get(src)
        row["created_by"] = created_by(order, script_uids, demo)
        rows.append(row)
    return pd.DataFrame(rows)


def finish(df: pd.DataFrame, dates: Sequence[str], m2o: Sequence[str], week_from: Optional[str]) -> pd.DataFrame:
    """Flatten many2one columns into *_id / *_name, parse dates, add a week bucket."""
    if df.empty:
        return df
    df = df.copy()
    for col in m2o:
        if col in df:
            df[f"{col}_id"] = df[col].map(m2o_id)
            df[f"{col}_name"] = df[col].map(m2o_name)
            df = df.drop(columns=[col])
    if "product_name" in df:
        df["product_code"] = df["product_name"].map(product_code)
    for col in dates:
        if col in df:
            df[col] = df[col].map(odoo_date)
    if week_from and week_from in df:
        df["week"] = df[week_from].map(week_start)
    return df


# ---------------------------------------------------------------------------
# extract (reads Odoo)
# ---------------------------------------------------------------------------


def has_key_field(o: Odoo, model: str) -> bool:
    return PPS_KEY in o.call(model, "fields_get", allfields=[PPS_KEY], attributes=["type"])


def extract(o: Odoo, demo: bool) -> Dict[str, pd.DataFrame]:
    key = [PPS_KEY] if not demo and has_key_field(o, "sale.order") else []
    bots = o.search_read("res.users", [["login", "in", ["pps-bot"]]], ["id"]) if not demo else []
    script_uids = {u["id"] for u in bots}
    t: Dict[str, pd.DataFrame] = {}

    prods = o.search_read("product.product", [["active", "in", [True, False]]],
                          ["default_code", "name", "uom_id", "sale_ok", "purchase_ok", "is_storable"])
    t["dim_product"] = finish(pd.DataFrame(prods).rename(columns={"id": "product_id", "default_code": "product_code",
                                                                   "uom_id": "uom"}),
                              [], ["uom"], None)

    parts = o.search_read("res.partner", [["is_company", "=", True]],
                          ["name", "supplier_rank", "customer_rank", "create_uid", *key])
    dp = pd.DataFrame(parts)
    if not dp.empty:
        dp["role"] = [("supplier" if s else "") + ("+" if s and c else "") + ("customer" if c else "") or "other"
                      for s, c in zip(dp["supplier_rank"], dp["customer_rank"])]
        dp["created_by"] = [created_by(r, script_uids, demo) for r in parts]
        dp = dp.drop(columns=[c for c in ("create_uid", PPS_KEY) if c in dp]).rename(columns={"id": "partner_id"})
    t["dim_partner"] = dp

    so = o.search_read("sale.order", [], ["name", "date_order", "commitment_date", "partner_id", "state",
                                          "create_uid", *key])
    sol = o.search_read("sale.order.line", [["order_id", "in", [r["id"] for r in so]]],
                        ["order_id", "product_id", "product_uom_qty", "qty_delivered", "price_unit", "price_subtotal"])
    t["fact_sales"] = finish(lines_with_orders(
        sol, so,
        {"product": "product_id", "qty_ordered": "product_uom_qty", "qty_delivered": "qty_delivered",
         "price_unit": "price_unit", "amount": "price_subtotal"},
        {"date_order": "date_order", "date_promised": "commitment_date", "customer": "partner_id", "state": "state"},
        script_uids, demo), ["date_order", "date_promised"], ["product", "customer"], "date_promised")

    po = o.search_read("purchase.order", [], ["name", "date_order", "partner_id", "state", "origin", "create_uid", *key])
    pol = o.search_read("purchase.order.line", [["order_id", "in", [r["id"] for r in po]]],
                        ["order_id", "product_id", "product_qty", "qty_received", "price_unit", "price_subtotal",
                         "date_planned"])
    t["fact_purchases"] = finish(lines_with_orders(
        pol, po,
        {"product": "product_id", "qty_ordered": "product_qty", "qty_received": "qty_received",
         "price_unit": "price_unit", "amount": "price_subtotal", "date_planned": "date_planned"},
        {"date_order": "date_order", "vendor": "partner_id", "state": "state", "origin": "origin"},
        script_uids, demo), ["date_order", "date_planned"], ["product", "vendor"], "date_planned")

    mos = o.search_read("mrp.production", [], ["name", "product_id", "product_qty", "qty_produced", "date_start",
                                               "date_finished", "state", "origin", "create_uid", *key])
    mo = pd.DataFrame(mos)
    if not mo.empty:
        mo["created_by"] = [created_by(r, script_uids, demo) for r in mos]
        mo = mo.drop(columns=[c for c in ("create_uid", PPS_KEY) if c in mo]).rename(
            columns={"id": "mo_id", "name": "mo_ref", "product_id": "product"})
    t["fact_production"] = finish(mo, ["date_start", "date_finished"], ["product"], "date_start")

    quants = o.search_read("stock.quant", [["location_id.usage", "=", "internal"]],
                           ["product_id", "location_id", "quantity", "reserved_quantity"])
    t["fact_stock"] = finish(pd.DataFrame(quants).rename(columns={"id": "quant_id", "product_id": "product",
                                                                   "location_id": "location"}),
                             [], ["product", "location"], None)

    ops = o.search_read("stock.warehouse.orderpoint", [], ["product_id", "product_min_qty", "product_max_qty",
                                                          "trigger", "qty_on_hand", "qty_forecast", "qty_to_order"])
    t["fact_reorder"] = finish(pd.DataFrame(ops).rename(columns={"id": "orderpoint_id", "product_id": "product"}),
                               [], ["product"], None)
    return t


def write(tables: Dict[str, pd.DataFrame], db: str, outdir: Path) -> Path:
    import duckdb

    target = outdir / db
    target.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    meta = pd.DataFrame([{"extracted_at_utc": now.isoformat(), "database": db,
                          **{f"rows_{k}": len(v) for k, v in tables.items()}}])
    tables = {**tables, "meta": meta}
    tmp = target / "pps.duckdb.tmp"
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    for name, df in tables.items():
        df.to_csv(target / f"{name}.csv", index=False)
        con.register("df_view", df if not df.empty else pd.DataFrame({"empty": []}))
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df_view")
        con.unregister("df_view")
    con.close()
    os.replace(tmp, target / "pps.duckdb")  # atomic: readers never see a half-written file
    return target


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=("live", "demo"), default="live")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    if args.source == "live":
        o = Odoo.reader()
    else:
        o = ReadOnlyOdoo()  # the demo's admin key, but the client refuses anything but reads
    tables = extract(o, demo=args.source == "demo")
    target = write(tables, o.db, args.out)
    counts = ", ".join(f"{k} {len(v)}" for k, v in tables.items())
    print(f"extracted {o.db} -> {target.relative_to(ROOT)}  ({counts})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
