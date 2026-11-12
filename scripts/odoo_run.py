"""Run Odoo's replenishment scheduler and export the resulting plan.

    .venv/bin/python scripts/odoo_run.py

Calls stock.rule.run_scheduler (the same job as Inventory > Operations > Run
Scheduler), then exports manufacturing orders and purchase order lines to
data/processed/odoo_plan.csv. Orders created by the seed as starting state
(origin "... at start [mock]") are flagged as open orders, not as planned output, and
the draft RFQs of the sourcing round (origin "RFQ round [mock]") are flagged as quotes.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import Odoo, OdooError  # noqa: E402

OUT = ROOT / "data" / "processed" / "odoo_plan.csv"
COLUMNS = ["kind", "reference", "item", "qty", "uom", "start", "due", "partner", "state", "origin", "open_at_start", "rfq"]
RFQ_ORIGIN = "RFQ round [mock]"


def code(display_name: str) -> str:
    """'[BLG-PWD] rBLG protein powder' -> 'BLG-PWD'."""
    return display_name[1 : display_name.index("]")] if display_name.startswith("[") else display_name


def main() -> int:
    o = Odoo()
    o.call("stock.rule", "run_scheduler")

    rows = []
    for m in o.search_read(
        "mrp.production",
        [["state", "not in", ["cancel"]]],
        ["name", "product_id", "product_qty", "product_uom_id", "date_start", "date_finished", "state", "origin"],
        order="date_start, id",
    ):
        rows.append({
            "kind": "MO", "reference": m["name"], "item": code(m["product_id"][1]), "qty": m["product_qty"],
            "uom": m["product_uom_id"][1], "start": m["date_start"], "due": m["date_finished"], "partner": "",
            "state": m["state"], "origin": m["origin"] or "", "open_at_start": "at start" in (m["origin"] or ""),
            "rfq": False,
        })
    for line in o.search_read(
        "purchase.order.line",
        [["state", "!=", "cancel"]],
        ["order_id", "product_id", "product_qty", "product_uom_id", "date_planned", "partner_id", "state"],
        order="date_planned, id",
    ):
        order = o.search_read("purchase.order", [["id", "=", line["order_id"][0]]], ["origin", "date_order"])[0]
        rows.append({
            "kind": "PO", "reference": line["order_id"][1], "item": code(line["product_id"][1]), "qty": line["product_qty"],
            "uom": line["product_uom_id"][1], "start": order["date_order"], "due": line["date_planned"],
            "partner": line["partner_id"][1], "state": line["state"], "origin": order["origin"] or "",
            "open_at_start": "at start" in (order["origin"] or ""),
            "rfq": (order["origin"] or "").startswith(RFQ_ORIGIN),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    mos = sum(r["kind"] == "MO" and not r["open_at_start"] and not r["rfq"] for r in rows)
    pos = sum(r["kind"] == "PO" and not r["open_at_start"] and not r["rfq"] for r in rows)
    rfq = sum(bool(r["rfq"]) for r in rows)
    print(f"scheduler ran; exported {mos} planned MOs, {pos} planned PO lines and "
          f"{rfq} RFQ lines from the sourcing round to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
