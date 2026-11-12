"""Create the RFQ round in Odoo: one draft request for quotation per bidding supplier.

    .venv/bin/python scripts/odoo_sourcing.py products/blg_whey_protein.yaml

Run this **after** the replenishment run and the plan comparison. In Odoo a draft
purchase order *is* an RFQ, and `stock.warehouse.orderpoint` counts draft, sent and
to-approve purchase lines as **replenishment already in progress**. A bid round seeded
at the horizon volume therefore tells the reorder rules that everything is on order, and
the scheduler creates no purchase orders at all (verified 2026-10-04: glucose forecast
went to +7.2 Mkg and every item's `qty_to_order` to 0). So the award lives on the vendor
price list, which `odoo_seed.py` writes, and the bid documents come last.

The quotes are **mock** and the suppliers fictional; the volume quoted is the horizon
requirement the award was decided on.
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

META = ROOT / "outputs" / "odoo" / "seed_meta.json"
RFQ_ORIGIN = "RFQ round [mock]"


def rfq_lines(cfg, res, items):
    """One request for quotation per bidding supplier: {supplier id: [(item, qty, price)]}.

    Pure function, so what Odoo would receive is testable offline.
    """
    if res.quotes is None or res.usage is None:
        return {}
    out = {}
    for iid in items:
        if iid not in res.usage.index:
            continue
        qty = float(res.usage.loc[iid, "gross_requirements"])
        if qty <= 0:
            continue
        for _, q in res.quotes[res.quotes["item"] == iid].sort_values("rank").iterrows():
            out.setdefault(q["supplier"], []).append((iid, round(qty, 4), round(float(q["quoted_usd_per_uom"]), 4)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not cfg.suppliers:
        print("no suppliers in the config: nothing to quote")
        return 0
    res = run(cfg, fetch_prices=False)
    planned = bom_mod.reachable(cfg.demand.item, cfg.bom)
    purchased = [i for i in planned if cfg.items[i].type == "purchased"]
    rfqs = rfq_lines(cfg, res, purchased)

    o = Odoo()
    if o.search_read("purchase.order", [["origin", "=", RFQ_ORIGIN]], ["id"], limit=1):
        raise SystemExit(f"the RFQ round already exists; rebuild with `make odoo-demo`")
    meta = json.loads(META.read_text()) if META.exists() else {}
    date_planned = f"{meta.get('anchor_week0', dt.date.today().isoformat())} 12:00:00"

    partner = {}
    for sid in rfqs:
        found = o.search_read("res.partner", [["name", "=", cfg.suppliers[sid].name]], ["id"], limit=1)
        if not found:
            raise SystemExit(f"{sid}: supplier not found in Odoo; run the seed first")
        partner[sid] = found[0]["id"]

    created = 0
    for sid, lines in rfqs.items():
        order_line = []
        for iid, qty, price in lines:
            prod = o.search_read("product.product", [["default_code", "=", iid]], ["id"], limit=1)
            if not prod:
                raise SystemExit(f"{iid}: product not found in Odoo; run the seed first")
            order_line.append([0, 0, {
                "product_id": prod[0]["id"], "product_qty": qty, "price_unit": price, "date_planned": date_planned,
            }])
        o.create("purchase.order", {"partner_id": partner[sid], "origin": RFQ_ORIGIN, "order_line": order_line})
        created += 1

    awards = res.awards
    print(f"created {created} draft RFQs covering {len(purchased)} item(s) (quotes are MOCK). "
          f"Purchase > Requests for Quotation shows the round.")
    for iid, aw in awards.iterrows():
        if iid in purchased:
            print(f"  {iid}: awarded to {aw['awarded_name']} at ${aw['awarded_usd_per_uom']:,.4g}/{aw['uom']} "
                  f"(price list sequence 1)")
    print("note: these drafts now count as replenishment in progress, so re-running the "
          "scheduler will not raise new POs until they are confirmed or cancelled.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
