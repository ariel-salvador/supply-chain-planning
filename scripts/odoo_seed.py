"""Load a product config into Odoo 19 Community via the JSON-2 API.

    .venv/bin/python scripts/odoo_seed.py products/blg_whey_protein.yaml

Everything comes from the product YAML and the assumptions registry (cited or mock);
company, vendor and customer names are fictional and say so. Creates:

  company name + replenishment horizon, units of measure (batch / lot units),
  partners tagged as vendors or customers so the two lists stay separate,
  products with routes (manufacture / buy), vendor price lists (one per bidder, with
  quoted price, lead time and minimum quantity, the awarded supplier first),
  bills of materials per batch, reorder rules, opening stock, open orders
  (WIP manufacturing orders and open purchase orders), and weekly demand as
  confirmed sales orders.

The RFQ round is **not** seeded here: a draft purchase order counts as replenishment
already in progress, so seeding one at the horizon volume stops the reorder rules from
ordering anything. It is created by scripts/odoo_sourcing.py after the planning run.

Dates: engine week 0 maps to the Monday after today, so Odoo's "today"-based
scheduler sees the same relative horizon. The mapping is written to
outputs/odoo/seed_meta.json for compare_plans.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import Odoo, OdooError  # noqa: E402
from ppsim import bom as bom_mod  # noqa: E402
from ppsim.config import load_config  # noqa: E402
from ppsim.pipeline import run  # noqa: E402
from ppsim.registry import load_registry  # noqa: E402

UOM_XMLID = {"kg": "uom.product_uom_kgm", "unit": "uom.product_uom_unit"}
META = ROOT / "outputs" / "odoo" / "seed_meta.json"
def supplier_prices(cfg, res, days_per_week: float, items):
    """Vendor price list rows: one per (item, bidder), awarded supplier first.

    Odoo replenishes from the lowest-``sequence`` ``product.supplierinfo`` line, so
    putting the awarded supplier at sequence 1 makes the RFQ award the default source.
    Pure function: returns (item, supplier id, vals) with no Odoo call, so it can be
    tested offline.
    """
    if res.quotes is None or res.awards is None:
        return []
    out = []
    for iid in items:
        bids = res.quotes[res.quotes["item"] == iid].sort_values("rank")
        for _, q in bids.iterrows():
            out.append((iid, q["supplier"], {
                "price": round(float(q["quoted_usd_per_uom"]), 4),
                "min_qty": round(float(q["moq_qty"]), 4),
                "delay": int(round(float(q["lead_time_weeks"]) * days_per_week)),
                "sequence": int(q["rank"]),
            }))
    return out


def anchor_monday(today: dt.date) -> dt.date:
    return today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)


def at_noon(d: dt.date) -> str:
    return f"{d.isoformat()} 12:00:00"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    args = ap.parse_args()

    cfg = load_config(args.config)
    res = run(cfg, fetch_prices=False)
    registry = load_registry(ROOT / "knowledge" / "assumptions.csv")
    if "days_per_week" not in registry:
        raise SystemExit("assumption 'days_per_week' is required to convert week lead times to days")
    days_per_week = registry["days_per_week"].value

    root = cfg.demand.item
    planned = bom_mod.reachable(root, cfg.bom)
    bom_lines = [b for b in cfg.bom if b.parent in planned]
    anchor = anchor_monday(dt.date.today())
    week = lambda t: anchor + dt.timedelta(days=int(days_per_week) * t)  # noqa: E731

    o = Odoo()
    if o.search_read("product.product", [["default_code", "=", root]], ["id"]):
        raise SystemExit("database already seeded; rebuild with `make odoo-demo`")

    # --- company, precision -------------------------------------------------
    company = o.search_read("res.company", [], ["id"], limit=1)[0]["id"]
    o.write("res.company", [company], {
        "name": cfg.company.name if cfg.company else "Demo company (fictional)",
        "horizon_days": cfg.horizon * days_per_week,  # same look-ahead as the engine
    })
    prec = o.search_read("decimal.precision", [["name", "=", "Product Unit"]], ["id"])
    o.write("decimal.precision", [prec[0]["id"]], {"digits": 4})

    # --- units --------------------------------------------------------------
    uom = {k: o.ref(x) for k, x in UOM_XMLID.items()}

    def lot_uom(name: str, base: str, factor: float) -> int:
        return o.create("uom.uom", {"name": name, "relative_uom_id": uom[base], "relative_factor": factor})

    # --- partners -----------------------------------------------------------
    # Odoo keeps one res.partner table for everyone; `supplier_rank` and `customer_rank`
    # are what make the Vendors and Customers lists (and the PO / SO dropdowns) filter
    # to the right side. Without them every partner shows up in both.
    partner = {}
    bidders = cfg.suppliers or cfg.vendors          # the supplier master, or the M3 vendor list
    for p in bidders.values():
        partner[p.id] = o.create("res.partner", {"name": p.name, "is_company": True, "supplier_rank": 1})
    for p in cfg.customers.values():
        partner[p.id] = o.create("res.partner", {"name": p.name, "is_company": True, "customer_rank": 1})
    if res.awards is not None:
        vendor_of = {i: r["awarded_to"] for i, r in res.awards.iterrows()}   # the RFQ award decides
    else:
        vendor_of = {i: v.id for v in bidders.values() for i in v.supplies}
    customer_ids = [c.id for c in cfg.customers.values()]

    # --- products -----------------------------------------------------------
    route = {
        "make": o.ref("mrp.route_warehouse0_manufacture"),
        "buy": o.ref("purchase_stock.route_warehouse0_buy"),
    }
    wh = o.search_read("stock.warehouse", [], ["lot_stock_id"], limit=1)[0]
    stock_loc = wh["lot_stock_id"][0]
    o.write("stock.warehouse", [wh["id"]], {"name": "Demo Plant (fictional)"})
    tmpl, prod, repl_uom = {}, {}, {}
    for iid in planned:
        it = cfg.items[iid]
        if it.uom not in uom:
            raise SystemExit(f"{iid}: unsupported uom {it.uom!r} (add it to UOM_XMLID)")
        buy = it.type == "purchased"
        tmpl[iid] = o.create("product.template", {
            "name": it.name,
            "default_code": iid,
            "type": "consu",
            "is_storable": True,
            "uom_id": uom[it.uom],
            "sale_ok": it.type == "finished",
            "purchase_ok": buy,
            "route_ids": [[6, 0, [route["buy" if buy else "make"]]]],
        })
        prod[iid] = o.search_read("product.product", [["product_tmpl_id", "=", tmpl[iid]]], ["id"])[0]["id"]

        lot = it.planning.lot_sizing
        if lot.rule == "fixed_order_quantity":
            repl_uom[iid] = lot_uom(f"{iid} lot ({lot.quantity:,.0f} {it.uom})", it.uom, lot.quantity)
        elif lot.multiple > 1:
            repl_uom[iid] = lot_uom(f"{iid} batch ({lot.multiple:,.0f} {it.uom})", it.uom, lot.multiple)

        if buy and iid not in vendor_of:
            raise SystemExit(f"{iid}: no vendor supplies this purchased item")

    # --- vendor price lists (every bidder; the awarded supplier at sequence 1) ---
    quoted = supplier_prices(cfg, res, days_per_week, [i for i in planned if cfg.items[i].type == "purchased"])
    for iid, sid, vals in quoted:
        o.create("product.supplierinfo", {"partner_id": partner[sid], "product_tmpl_id": tmpl[iid], **vals})
    for iid in [i for i in planned if cfg.items[i].type == "purchased"]:
        if any(q[0] == iid for q in quoted):
            continue                                 # already has quoted price-list lines
        lot = cfg.items[iid].planning.lot_sizing
        o.create("product.supplierinfo", {
            "partner_id": partner[vendor_of[iid]],
            "product_tmpl_id": tmpl[iid],
            "min_qty": lot.quantity if lot.rule == "fixed_order_quantity" else lot.minimum,
            "delay": int(cfg.items[iid].planning.lead_time * days_per_week),
        })

    # --- bills of materials (one per manufactured item, per batch) ----------
    for parent in [i for i in planned if cfg.items[i].type != "purchased"]:
        it = cfg.items[parent]
        base = it.batch_size or 1.0
        comps = [b for b in bom_lines if b.parent == parent]
        o.create("mrp.bom", {
            "product_tmpl_id": tmpl[parent],
            "product_qty": base,
            "product_uom_id": uom[it.uom],
            "type": "normal",
            "produce_delay": int(it.planning.lead_time * days_per_week),
            "bom_line_ids": [[0, 0, {
                "product_id": prod[b.component],
                "product_qty": round(b.qty_per * base, 4),
                "product_uom_id": uom[cfg.items[b.component].uom],
            }] for b in comps],
        })

    # --- reorder rules (min = max = safety stock; lot/batch unit as multiple) ---
    for iid in planned:
        ss = cfg.items[iid].planning.safety_stock
        vals = {
            "product_id": prod[iid],
            "location_id": stock_loc,
            "product_min_qty": ss,
            "product_max_qty": ss,
            "trigger": "auto",
        }
        if iid in repl_uom:
            vals["replenishment_uom_id"] = repl_uom[iid]
        o.create("stock.warehouse.orderpoint", vals)

    # --- opening stock ------------------------------------------------------
    quants = [
        o.call("stock.quant", "create", vals_list=[{
            "product_id": prod[i], "location_id": stock_loc, "inventory_quantity": cfg.items[i].planning.on_hand,
        }], context={"inventory_mode": True})[0]
        for i in planned if cfg.items[i].planning.on_hand > 0
    ]
    if quants:
        o.call("stock.quant", "action_apply_inventory", ids=quants)

    # --- open orders (scheduled receipts) -----------------------------------
    for iid in planned:
        it = cfg.items[iid]
        for t, q in sorted(it.planning.scheduled_receipts.items()):
            due = at_noon(week(t))
            if it.type == "purchased":
                po = o.create("purchase.order", {
                    "partner_id": partner[vendor_of[iid]],
                    "origin": "Open PO at start [mock]",
                    "order_line": [[0, 0, {"product_id": prod[iid], "product_qty": q, "date_planned": due}]],
                })
                o.call("purchase.order", "button_confirm", ids=[po])
            else:
                # work in progress: no BOM, so it doesn't consume components again
                mo = o.create("mrp.production", {
                    "product_id": prod[iid],
                    "product_qty": q,
                    "product_uom_id": uom[it.uom],
                    "bom_id": False,
                    "date_start": due,
                    "origin": "WIP at start [mock]",
                })
                o.call("mrp.production", "action_confirm", ids=[mo])

    # --- demand: one confirmed sales order per week -------------------------
    weekly = (
        res.mps.table.loc["projected_demand"].to_numpy()
        if res.mps is not None
        else res.demand["qty"].to_numpy()[: cfg.horizon]
    )
    for t, q in enumerate(weekly):
        if q <= 0:
            continue
        # round-robin across customers: structural presentation only, since the engine
        # plans on aggregate demand and does not model demand per customer
        so = o.create("sale.order", {
            "partner_id": partner[customer_ids[t % len(customer_ids)]],
            "commitment_date": at_noon(week(t)),
            "client_order_ref": f"Week {t} demand [mock]",
            "order_line": [[0, 0, {"product_id": prod[root], "product_uom_qty": round(float(q), 2)}]],
        })
        o.call("sale.order", "action_confirm", ids=[so])

    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps({
        "supplierinfo_rows": len(quoted),
        "awarded_supplier": {i: vendor_of[i] for i in sorted(vendor_of)},
        "config": str(args.config),
        "anchor_week0": anchor.isoformat(),
        "engine_week0": cfg.start,
        "days_per_week": days_per_week,
        "horizon_weeks": cfg.horizon,
        "products": {i: prod[i] for i in planned},
    }, indent=2))
    print(f"seeded {len(planned)} products, {len(bom_lines)} BOM lines, {len(quoted)} vendor price-list "
          f"lines, {len(weekly)} weekly sales orders; engine week 0 ({cfg.start}) -> Odoo {anchor}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
