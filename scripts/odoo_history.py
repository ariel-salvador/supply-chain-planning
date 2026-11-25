"""Write the MOCK operating history into Odoo (ADR 0018).

    .venv/bin/python scripts/odoo_history.py products/blg_whey_protein.yaml --target rehearsal  # pps_demo copy
    .venv/bin/python scripts/odoo_history.py products/blg_whey_protein.yaml --target live       # pps_live
    ... --until 2024-03-31     # stop after a date (resume later; reruns skip what is done)
    ... --plan-only            # print the document counts, touch nothing

``ppsim.history.simulate`` decides what happened each week; this script replays it in
date order as the ``pps-bot`` user: opening stock, purchase orders and receipts, vendor
bills and payments, manufacturing orders, the scrapped batch, sales orders, deliveries,
customer invoices and payments. Every document is **backdated** to its week.

Rules (ADR 0017/0018):
- append-only and resumable: each root document carries ``x_pps_key`` (``hist:...``); a
  rerun looks it up and only advances it to the state the ledger says (confirm,
  receive/deliver, bill/invoice, pay). It never edits a field it didn't just set, never
  deletes, and never touches records without a ``hist:`` key;
- nothing in the past stays open: every past order is received/delivered, billed and
  invoiced; only orders due after the history end stay open, and invoices whose
  payment falls after it;
- no chatter: tracking and log messages are switched off for the backfill.
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import PPS_KEY, Odoo, OdooError  # noqa: E402

LEDGER = ROOT / "outputs" / "history"
CTX = {"tracking_disable": True, "mail_notrack": True, "mail_create_nolog": True,
       "mail_auto_subscribe_no_notify": True}
NO_BACKORDER = {"skip_backorder": True}
# same-timestamp order: stock must arrive before it is used, documents before payments
RANK = {"opening": 0, "po": 1, "so": 2, "receipt": 3, "bill": 4, "mo": 5, "scrap": 6,
        "delivery": 7, "invoice": 8, "pay_in": 9, "pay_out": 9}
OPENING_KEY = "hist:opening"
MOCK = "[mock]"


@dataclass(frozen=True)
class Action:
    when: pd.Timestamp
    kind: str
    key: str                      # the root document's x_pps_key
    data: Dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def sort_key(self) -> tuple:
        return (self.when, RANK[self.kind], self.key)


def dt(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def d(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# plan (pure, tested)
# ---------------------------------------------------------------------------


def actions(hist) -> List[Action]:
    """Every step of every document, in the order it happened."""
    out: List[Action] = []
    first = hist.weeks[0] - pd.Timedelta(days=1) + pd.Timedelta(hours=12)
    out.append(Action(first, "opening", OPENING_KEY, {"qty": {i: q for i, q in hist.opening.items() if q > 0}}))

    for key, g in hist.purchases.groupby("key", sort=False):
        r = g.iloc[0]
        lines = [{"item": x.item, "qty": x.qty, "qty_received": x.qty_received, "price_unit": x.price_unit}
                 for x in g.itertuples()]
        out.append(Action(r.date_order, "po", key, {"supplier": r.supplier, "date_promised": r.date_promised,
                                                    "emergency": bool(r.emergency), "lines": lines}))
        if pd.notna(r.date_received):
            out.append(Action(r.date_received, "receipt", key, {"lines": lines}))
            out.append(Action(r.date_received, "bill", key, {"bill_date": r.bill_date, "due": r.bill_due}))
            if pd.notna(r.date_paid):
                out.append(Action(r.date_paid, "pay_out", key, {}))

    for b in hist.production.itertuples():
        out.append(Action(b.date_start, "mo", b.key, {"product": b.product, "qty": b.qty,
                                                      "date_finished": b.date_finished, "batch": b.batch}))
        if b.scrapped:
            out.append(Action(b.date_finished, "scrap", b.key, {"product": b.product, "qty": b.qty}))

    for s in hist.sales.itertuples():
        out.append(Action(s.date_order, "so", s.key, {"customer": s.customer, "qty": s.qty, "price_unit": s.price_unit,
                                                      "date_promised": s.date_promised, "spike": bool(s.spike)}))
        if pd.notna(s.date_shipped):
            out.append(Action(s.date_shipped, "delivery", s.key, {"qty": s.qty}))
            out.append(Action(s.date_shipped, "invoice", s.key, {"invoice_date": s.invoice_date, "due": s.invoice_due}))
            if pd.notna(s.date_paid):
                out.append(Action(s.date_paid, "pay_in", s.key, {}))
    return sorted(out, key=lambda a: a.sort_key)


def summary(acts: Sequence[Action]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for a in acts:
        out[a.kind] = out.get(a.kind, 0) + 1
    return out


# ---------------------------------------------------------------------------
# writer (talks to Odoo)
# ---------------------------------------------------------------------------


class Writer:
    def __init__(self, o: Odoo, cfg):
        self.o, self.cfg = o, cfg
        self.calls = 0
        self.done: Dict[str, int] = {}
        prods = o.search_read("product.product", [["default_code", "!=", False]], ["default_code"])
        self.prod = {p["default_code"]: p["id"] for p in prods}
        parts = o.search_read("res.partner", [[PPS_KEY, "like", "partner:"]], [PPS_KEY])
        self.partner = {p[PPS_KEY].split(":", 1)[1]: p["id"] for p in parts}
        self.bom = {}
        for b in o.search_read("mrp.bom", [[PPS_KEY, "like", "bom:"]], [PPS_KEY]):
            self.bom[b[PPS_KEY].split(":", 1)[1]] = b["id"]
        self.stock = o.ref("stock.stock_location_stock")
        self.inventory_loc = o.search_read("stock.location", [["usage", "=", "inventory"]], ["id"], limit=1)[0]["id"]
        self.bank = o.search_read("account.journal", [["type", "=", "bank"]], ["id"], limit=1)[0]["id"]
        self.ids: Dict[str, Dict[str, int]] = {}
        for model in ("sale.order", "purchase.order", "mrp.production", "stock.picking", "account.move"):
            rows = o.search_read(model, [[PPS_KEY, "like", "hist:"]], [PPS_KEY])
            self.ids[model] = {r[PPS_KEY]: r["id"] for r in rows}

    # -- plumbing --------------------------------------------------------------
    def c(self, model: str, method: str, ids: Sequence[int] = (), context: Optional[dict] = None, **kw: Any) -> Any:
        self.calls += 1
        return self.o.call(model, method, ids=ids, context={**CTX, **(context or {})}, **kw)

    def create(self, model: str, vals: dict, context: Optional[dict] = None) -> int:
        return self.c(model, "create", vals_list=[vals], context=context)[0]

    def read(self, model: str, rid: int, fields: List[str]) -> dict:
        return self.c(model, "read", [rid], fields=fields)[0]

    def count(self, kind: str) -> None:
        self.done[kind] = self.done.get(kind, 0) + 1

    def backdate_moves(self, domain: list, when: pd.Timestamp) -> None:
        moves = [m["id"] for m in self.c("stock.move", "search_read", domain=domain, fields=["id"])]
        if moves:
            self.c("stock.move", "write", moves, vals={"date": dt(when)})
            lines = [m["id"] for m in self.c("stock.move.line", "search_read", domain=[["move_id", "in", moves]],
                                             fields=["id"])]
            if lines:
                self.c("stock.move.line", "write", lines, vals={"date": dt(when)})

    def validate_picking(self, pid: int, qty_by_product: Dict[int, float], when: pd.Timestamp) -> None:
        """Set done quantities (short ones close the move: no backorder), validate, backdate."""
        pk = self.read("stock.picking", pid, ["state", "picking_type_code"])
        if pk["state"] == "cancel":
            return
        if pk["state"] != "done":
            if pk["picking_type_code"] == "outgoing":
                self.c("stock.picking", "action_assign", [pid])
            moves = self.c("stock.move", "search_read", domain=[["picking_id", "=", pid]],
                           fields=["product_id", "product_uom_qty"])
            for m in moves:
                q = qty_by_product.get(m["product_id"][0], m["product_uom_qty"])
                self.c("stock.move", "write", [m["id"]], vals={"quantity": round(q, 4), "picked": True})
            res = self.c("stock.picking", "button_validate", [pid], context={**NO_BACKORDER,
                                                                             "picking_ids_not_to_backorder": [pid]})
            if res is not True and self.read("stock.picking", pid, ["state"])["state"] != "done":
                raise OdooError(f"picking {pid} not validated: {str(res)[:200]}")
        self.c("stock.picking", "write", [pid], vals={"date_done": dt(when), "scheduled_date": dt(when)})
        self.backdate_moves([["picking_id", "=", pid]], when)

    def invoice_post(self, mid: int, key: str, inv_date: pd.Timestamp, due: pd.Timestamp, ref: Optional[str]) -> None:
        mv = self.read("account.move", mid, ["state"])
        if mv["state"] == "draft":
            vals = {"invoice_date": d(inv_date), "date": d(inv_date), "invoice_date_due": d(due), PPS_KEY: key}
            if ref:
                vals["ref"] = ref
            self.c("account.move", "write", [mid], vals=vals)
            self.c("account.move", "action_post", [mid])

    def pay(self, mid: int, when: pd.Timestamp) -> None:
        mv = self.read("account.move", mid, ["state", "payment_state"])
        if mv["state"] != "posted" or mv["payment_state"] in ("paid", "in_payment", "reversed"):
            return
        ctx = {"active_model": "account.move", "active_ids": [mid]}
        wiz = self.create("account.payment.register", {"payment_date": d(when), "journal_id": self.bank}, context=ctx)
        self.c("account.payment.register", "action_create_payments", [wiz], context=ctx)

    # -- one step --------------------------------------------------------------
    def apply(self, a: Action) -> None:
        getattr(self, f"do_{a.kind}")(a)
        self.count(a.kind)

    def do_opening(self, a: Action) -> None:
        pid = self.ids["stock.picking"].get(a.key)
        if pid is None:
            pid = self.create("stock.picking", {
                "picking_type_id": self.o.ref("stock.picking_type_in"), "location_id": self.inventory_loc,
                "location_dest_id": self.stock, "origin": f"Opening stock {MOCK}", "scheduled_date": dt(a.when),
                PPS_KEY: a.key,
                "move_ids": [[0, 0, {"product_id": self.prod[i], "product_uom_qty": round(q, 4),
                                     "location_id": self.inventory_loc, "location_dest_id": self.stock}]
                             for i, q in a.data["qty"].items()],
            })
            self.ids["stock.picking"][a.key] = pid
            self.c("stock.picking", "action_confirm", [pid])
        self.validate_picking(pid, {}, a.when)

    def do_po(self, a: Action) -> None:
        pid = self.ids["purchase.order"].get(a.key)
        if pid is None:
            note = "Emergency buy during supplier outage " if a.data["emergency"] else ""
            pid = self.create("purchase.order", {
                "partner_id": self.partner[a.data["supplier"]], "date_order": dt(a.when),
                "date_planned": dt(a.data["date_promised"]), "origin": f"{note}History {MOCK}", PPS_KEY: a.key,
                "order_line": [[0, 0, {"product_id": self.prod[ln["item"]], "product_qty": ln["qty"],
                                       "price_unit": ln["price_unit"], "date_planned": dt(a.data["date_promised"]),
                                       "tax_ids": [[6, 0, []]]}] for ln in a.data["lines"]],
            })
            self.ids["purchase.order"][a.key] = pid
        if self.read("purchase.order", pid, ["state"])["state"] in ("draft", "sent"):
            self.c("purchase.order", "button_confirm", [pid])
            self.c("purchase.order", "write", [pid], vals={"date_order": dt(a.when), "date_approve": dt(a.when)})

    def do_receipt(self, a: Action) -> None:
        pid = self.ids["purchase.order"][a.key]
        qty = {self.prod[ln["item"]]: ln["qty_received"] for ln in a.data["lines"]}
        for pk in self.read("purchase.order", pid, ["picking_ids"])["picking_ids"]:
            self.validate_picking(pk, qty, a.when)

    def do_bill(self, a: Action) -> None:
        pid = self.ids["purchase.order"][a.key]
        po = self.read("purchase.order", pid, ["invoice_ids", "name"])
        if not po["invoice_ids"]:
            self.c("purchase.order", "action_create_invoice", [pid])
            po = self.read("purchase.order", pid, ["invoice_ids", "name"])
        bill_key = f"hist:bill:{a.key[len('hist:po:'):]}"
        for mid in po["invoice_ids"]:
            self.invoice_post(mid, bill_key, a.data["bill_date"], a.data["due"], ref=po["name"])
            self.ids["account.move"][bill_key] = mid

    def do_pay_out(self, a: Action) -> None:
        self.pay(self._move(f"hist:bill:{a.key[len('hist:po:'):]}", "purchase.order", a.key), a.when)

    def do_so(self, a: Action) -> None:
        sid = self.ids["sale.order"].get(a.key)
        if sid is None:
            ref = "Launch volume " if a.data["spike"] else ""
            sid = self.create("sale.order", {
                "partner_id": self.partner[a.data["customer"]], "date_order": dt(a.when),
                "commitment_date": dt(a.data["date_promised"]), "client_order_ref": f"{ref}History {MOCK}",
                PPS_KEY: a.key,
                "order_line": [[0, 0, {"product_id": self.prod[self.cfg.demand.item], "product_uom_qty": a.data["qty"],
                                       "price_unit": a.data["price_unit"], "tax_ids": [[6, 0, []]]}]],
            })
            self.ids["sale.order"][a.key] = sid
        if self.read("sale.order", sid, ["state"])["state"] in ("draft", "sent"):
            self.c("sale.order", "action_confirm", [sid])
            self.c("sale.order", "write", [sid], vals={"date_order": dt(a.when)})   # confirming stamps "now"

    def do_delivery(self, a: Action) -> None:
        sid = self.ids["sale.order"][a.key]
        for pk in self.read("sale.order", sid, ["picking_ids"])["picking_ids"]:
            self.validate_picking(pk, {}, a.when)

    def do_invoice(self, a: Action) -> None:
        sid = self.ids["sale.order"][a.key]
        so = self.read("sale.order", sid, ["invoice_ids"])
        if not so["invoice_ids"]:
            ctx = {"active_model": "sale.order", "active_ids": [sid], "active_id": sid}
            wiz = self.create("sale.advance.payment.inv", {"advance_payment_method": "delivered"}, context=ctx)
            self.c("sale.advance.payment.inv", "create_invoices", [wiz], context=ctx)
            so = self.read("sale.order", sid, ["invoice_ids"])
        inv_key = f"hist:inv:{a.key[len('hist:so:'):]}"
        for mid in so["invoice_ids"]:
            self.invoice_post(mid, inv_key, a.data["invoice_date"], a.data["due"], ref=None)
            self.ids["account.move"][inv_key] = mid

    def do_pay_in(self, a: Action) -> None:
        self.pay(self._move(f"hist:inv:{a.key[len('hist:so:'):]}", "sale.order", a.key), a.when)

    def _move(self, move_key: str, order_model: str, order_key: str) -> int:
        if move_key in self.ids["account.move"]:
            return self.ids["account.move"][move_key]
        inv = self.read(order_model, self.ids[order_model][order_key], ["invoice_ids"])["invoice_ids"]
        if len(inv) != 1:
            raise OdooError(f"{order_key}: expected one invoice, found {len(inv)}")
        return inv[0]

    def do_mo(self, a: Action) -> None:
        mid = self.ids["mrp.production"].get(a.key)
        if mid is None:
            mid = self.create("mrp.production", {
                "product_id": self.prod[a.data["product"]], "product_qty": a.data["qty"],
                "bom_id": self.bom[a.data["product"]], "date_start": dt(a.when),
                "origin": f"Batch {a.data['batch']} {MOCK}", PPS_KEY: a.key,
            })
            self.ids["mrp.production"][a.key] = mid
        state = self.read("mrp.production", mid, ["state"])["state"]
        if state == "draft":
            self.c("mrp.production", "action_confirm", [mid])
            state = "confirmed"
        if state not in ("done", "cancel"):
            res = self.c("mrp.production", "button_mark_done", [mid])
            if self.read("mrp.production", mid, ["state"])["state"] != "done":
                raise OdooError(f"{a.key}: manufacturing order not done: {str(res)[:200]}")
        fin = a.data["date_finished"]
        self.c("mrp.production", "write", [mid], vals={"date_start": dt(a.when), "date_finished": dt(fin)},
               context={"force_date": True})
        self.backdate_moves(["|", ["raw_material_production_id", "=", mid], ["production_id", "=", mid]], fin)

    def do_scrap(self, a: Action) -> None:
        mid = self.ids["mrp.production"][a.key]
        name = self.read("mrp.production", mid, ["name"])["name"]
        origin = f"Contaminated batch {name} {MOCK}"
        found = self.c("stock.scrap", "search_read", domain=[["origin", "=", origin]], fields=["state"])
        if found:
            sid = found[0]["id"]
        else:
            sid = self.create("stock.scrap", {"product_id": self.prod[a.data["product"]], "scrap_qty": a.data["qty"],
                                              "location_id": self.stock, "origin": origin})
        if self.read("stock.scrap", sid, ["state"])["state"] != "done":
            self.c("stock.scrap", "action_validate", [sid])
        when = a.when + pd.Timedelta(hours=1)
        self.c("stock.scrap", "write", [sid], vals={"date_done": dt(when)})
        self.backdate_moves([["scrap_id", "=", sid]], when)


def run_actions(w: Writer, acts: Sequence[Action], log_every: int = 250) -> None:
    t0 = time.time()
    for n, a in enumerate(acts, 1):
        try:
            w.apply(a)
        except OdooError as e:
            raise OdooError(f"step {n}/{len(acts)} {a.kind} {a.key} @ {a.when}: {e}") from None
        if n % log_every == 0 or n == len(acts):
            el = time.time() - t0
            print(f"  {n:5d}/{len(acts)}  through {a.when.date()}  {w.calls} calls  "
                  f"{el / 60:.1f} min elapsed, ~{el / n * (len(acts) - n) / 60:.0f} min left", flush=True)


def build(config: Path):
    from ppsim import history as H
    from ppsim.config import load_config
    from ppsim.pipeline import run

    cfg = load_config(config)
    res = run(cfg)                                   # FRED prices: cached, refreshed if stale
    if res.prices is None:
        raise SystemExit("no FRED prices available (run scripts/fetch_data.py); history needs the cited series")
    prices = res.prices.join(res.index_prices, how="outer") if res.index_prices is not None else res.prices
    hist = H.simulate(cfg, prices, res.quotes, res.awards)
    errs = H.conservation_errors(hist)
    if errs:
        raise SystemExit(f"ledger does not balance: {errs[:3]}")
    return cfg, hist


def write_ledger(hist, outdir: Path) -> None:
    """The engine side of the history, for checks and the dashboard marts (gitignored:
    prices derive from IMF series, which are not committable)."""
    outdir.mkdir(parents=True, exist_ok=True)
    k = hist.kpis
    k[["week", "forecast", "demand", "orders_due_qty"]].rename(columns={"orders_due_qty": "orders_qty"}) \
        .to_csv(outdir / "forecast.csv", index=False)
    hist.standards.to_csv(outdir / "standards.csv", index=False)
    hist.price_list.to_csv(outdir / "price_list.csv", index=False)
    k.to_csv(outdir / "kpis.csv", index=False)
    hist.flows.to_csv(outdir / "flows.csv", index=False)
    hist.events.to_csv(outdir / "events.csv", index=False)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    ap.add_argument("--target", choices=("live", "rehearsal"), required=True)
    ap.add_argument("--until", help="last date to write (YYYY-MM-DD); later steps wait for the next run")
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args(argv)

    cfg, hist = build(args.config)
    write_ledger(hist, LEDGER)
    acts = actions(hist)
    if args.until:
        acts = [a for a in acts if a.when <= pd.Timestamp(args.until) + pd.Timedelta(days=1)]
    print(f"history {hist.weeks[0].date()} -> {hist.end.date()}: {len(acts)} steps {summary(acts)}")
    for n in hist.notes:
        print(f"  note: {n}")
    if args.plan_only:
        return 0
    if args.target == "live":
        o = Odoo.live()
    else:
        import os
        o = Odoo.live(db=os.environ.get("ODOO_DB_NAME", "pps_demo"))   # the rehearsal copy has the same bot
    if not o.search_read("res.users", [["login", "=", "pps-bot"]], ["id"]):
        raise SystemExit(f"{o.db} has no pps-bot: for a rehearsal run `make odoo-history-rehearse`")
    w = Writer(o, cfg)
    print(f"writing to {o.db} as pps-bot ...", flush=True)
    run_actions(w, acts)
    print(f"done: {w.done}  ({w.calls} API calls)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
