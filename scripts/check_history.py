"""Check that Odoo holds exactly the history the engine simulated (ADR 0018). Read-only.

    .venv/bin/python scripts/check_history.py products/blg_whey_protein.yaml               # pps_live (pps-reader)
    .venv/bin/python scripts/check_history.py products/blg_whey_protein.yaml --db pps_demo  # the rehearsal

Compares, for the ``hist:`` documents only (manual work is ignored): on-hand stock per
item, revenue and purchase spend per year, receivables still open, delivery and
receipt dates, and that nothing due in the past is still open. Exit code 1 on any
mismatch.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import PPS_KEY, Odoo, ReadOnlyOdoo  # noqa: E402
from odoo_history import build  # noqa: E402

TOL_QTY, TOL_USD = 0.01, 1.0


def check(o: Odoo, hist, cfg) -> List[str]:
    bad: List[str] = []
    end = hist.end + pd.Timedelta(hours=12)

    def say(ok: bool, what: str) -> None:
        print(("  ok   " if ok else "  FAIL ") + what)
        if not ok:
            bad.append(what)

    # stock on hand at the end = the ledger's closing stock
    prods = {p["id"]: p["default_code"] for p in o.search_read("product.product", [], ["default_code"])}
    quants = o.search_read("stock.quant", [["location_id.usage", "=", "internal"]], ["product_id", "quantity"])
    have = {}
    for q in quants:
        code = prods.get(q["product_id"][0])
        have[code] = have.get(code, 0.0) + q["quantity"]
    last = hist.flows[hist.flows["week"] == hist.weeks[-1]].set_index("item")["closing"]
    for item, want in last.items():
        say(abs(have.get(item, 0.0) - want) <= TOL_QTY, f"on hand {item}: odoo {have.get(item, 0.0):,.4f} vs ledger {want:,.4f}")

    # documents
    so = o.search_read("sale.order", [[PPS_KEY, "like", "hist:"]], [PPS_KEY, "state", "commitment_date", "effective_date",
                                                                  "date_order", "invoice_status"])
    po = o.search_read("purchase.order", [[PPS_KEY, "like", "hist:"]], [PPS_KEY, "state", "effective_date",
                                                                       "receipt_status", "invoice_status"])
    mo = o.search_read("mrp.production", [[PPS_KEY, "like", "hist:"]], [PPS_KEY, "state", "date_start", "date_finished"])
    say(len(so) == len(hist.sales), f"sales orders: {len(so)} vs {len(hist.sales)}")
    say(len(po) == hist.purchases["key"].nunique(), f"purchase orders: {len(po)} vs {hist.purchases['key'].nunique()}")
    say(len(mo) == len(hist.production) and all(m["state"] == "done" for m in mo),
        f"manufacturing orders done: {sum(m['state'] == 'done' for m in mo)} vs {len(hist.production)}")
    led = hist.sales.set_index("key")
    late = [s[PPS_KEY] for s in so if pd.Timestamp(s["commitment_date"]) <= end and s["invoice_status"] != "invoiced"]
    say(not late, f"past sales orders all delivered and invoiced ({len(late)} open)")
    wrong = [s[PPS_KEY] for s in so if s["effective_date"]
             and pd.Timestamp(s["effective_date"]) != led.loc[s[PPS_KEY], "date_shipped"]]
    say(not wrong, f"delivery dates match the ledger ({len(wrong)} differ)")
    wrong = [s[PPS_KEY] for s in so if pd.Timestamp(s["date_order"]) != led.loc[s[PPS_KEY], "date_order"]]
    say(not wrong, f"order dates match the ledger ({len(wrong)} differ)")
    pl = hist.purchases.groupby("key").first()
    wrong = [p[PPS_KEY] for p in po if p["effective_date"]
             and pd.Timestamp(p["effective_date"]) != pl.loc[p[PPS_KEY], "date_received"]]
    say(not wrong, f"receipt dates match the ledger ({len(wrong)} differ)")
    pol = o.search_read("purchase.order.line", [["order_id", "in", [p["id"] for p in po]]], ["order_id", "date_planned"])
    key_of = {p["id"]: p[PPS_KEY] for p in po}
    wrong = [l for l in pol if pd.Timestamp(l["date_planned"]) != pl.loc[key_of[l["order_id"][0]], "date_promised"]]
    say(not wrong, f"promised dates on PO lines unchanged ({len(wrong)} differ)")

    # money
    inv = o.search_read("account.move", [[PPS_KEY, "like", "hist:"], ["state", "=", "posted"]],
                        [PPS_KEY, "move_type", "invoice_date", "amount_total", "amount_residual"])
    df = pd.DataFrame(inv)
    df["year"] = pd.to_datetime(df["invoice_date"]).dt.year
    rev = df[df["move_type"] == "out_invoice"].groupby("year")["amount_total"].sum()
    s = hist.sales.dropna(subset=["invoice_date"])
    want = s.groupby(s["invoice_date"].dt.year)["amount"].sum()
    for y in want.index:
        say(abs(rev.get(y, 0) - want[y]) <= TOL_USD, f"revenue {y}: odoo {rev.get(y, 0):,.2f} vs ledger {want[y]:,.2f}")
    spend = df[df["move_type"] == "in_invoice"].groupby("year")["amount_total"].sum()
    p = hist.purchases.dropna(subset=["bill_date"])
    want = (p["qty_received"] * p["price_unit"]).groupby(p["bill_date"].dt.year).sum()
    for y in want.index:
        say(abs(spend.get(y, 0) - want[y]) <= TOL_USD * 10, f"purchases billed {y}: odoo {spend.get(y, 0):,.2f} vs ledger {want[y]:,.2f}")
    ar = df[(df["move_type"] == "out_invoice") & (df["amount_residual"] > 0.005)]
    want_open = hist.sales[hist.sales["invoice_date"].notna() & hist.sales["date_paid"].isna()]
    say(len(ar) == len(want_open) and abs(ar["amount_residual"].sum() - want_open["amount"].sum()) <= TOL_USD,
        f"open receivables: odoo {len(ar)} / {ar['amount_residual'].sum():,.2f} vs ledger {len(want_open)} / "
        f"{want_open['amount'].sum():,.2f}")
    return bad


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    ap.add_argument("--db", help="check this database with the bot key, read-only (e.g. the rehearsal)")
    args = ap.parse_args(argv)
    cfg, hist = build(args.config)
    o = ReadOnlyOdoo(db=args.db, key_file=".odoo-apikey-live") if args.db else Odoo.reader()
    print(f"checking {o.db} against the ledger ({hist.weeks[0].date()} -> {hist.end.date()})")
    bad = check(o, hist, cfg)
    print("all checks pass" if not bad else f"{len(bad)} check(s) failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
