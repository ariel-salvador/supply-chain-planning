"""MOCK operating history: the weekly ledger behind the ERP backfill (ADR 0018).

Simulates the plant week by week from ``history.start`` to ``history.end`` and returns
every document the ERP should hold, plus the stock flows and KPIs that check it:

- **demand** backcasts the plan's trend (``demand.generate`` anchored at ``time.start``,
  with its own seed), split across the fictional customers by share and order cadence;
  one named event adds unforecast volume;
- **sales**: each order is placed ``order_lead_weeks`` ahead and shipped whole, first
  due first, when powder is on hand. Late orders ship as soon as stock allows;
- **production**: whole fermentation batches, at most what the fermenters can run in a
  week (from the bill of resources), sized to keep powder above safety stock after the
  booked orders. Each batch is turned into powder the following week;
- **purchasing**: a reorder-point rule per purchased item from the awarded supplier,
  with its quoted lead time and minimum order (in weeks of usage). Deliveries are late
  or short at the supplier's quoted rates. An outage event makes the planner buy from
  the runner-up;
- **prices**: purchased items linked to a cited index (FRED) are bought at that month's
  should-cost target times the supplier's quote index; the rest at the mock base with
  the configured price drift. **Standard costs** are rolled every January from the
  December prices; the selling price is standard cost / (1 - target margin), set yearly;
- **finance**: invoices on shipment, customer payments after their usual days-to-pay,
  vendor bills paid on terms. Anything that would be paid after ``end`` stays open.

Pure: no Odoo, no network. ``prices`` (monthly USD per item uom, from
``feedstock.item_prices``) and the sourcing result are passed in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import demand as demand_mod
from . import sourcing as src_mod
from .config import ProductConfig

# Hour-of-day for every document (noon, so no time zone moves a date across midnight)
NOON = pd.Timedelta(hours=12)
# Weekday offsets inside a week (Monday = 0)
ORDER_DAY, RECEIPT_DAY, SHIP_DAY, PWD_DONE_DAY, FERM_DONE_DAY = 0, 0, 2, 4, 5
QTY_DIGITS = 4          # the ERP's "Product Unit" precision
PRICE_DIGITS = 4


@dataclass
class History:
    weeks: pd.DatetimeIndex                 # Monday of each history week
    sales: pd.DataFrame                     # one row per sales order (one line each)
    purchases: pd.DataFrame                 # one row per purchase order line
    production: pd.DataFrame                # one row per manufacturing order
    flows: pd.DataFrame                     # week x item: opening, in, out, closing
    standards: pd.DataFrame                 # year x item standard cost
    price_list: pd.DataFrame                # list price of the finished item over time
    kpis: pd.DataFrame                      # weekly KPI series
    events: pd.DataFrame                    # what happened, when
    opening: Dict[str, float]
    notes: List[str] = field(default_factory=list)

    @property
    def end(self) -> pd.Timestamp:
        return self.weeks[-1] + pd.Timedelta(days=6)


def _round(x: float, d: int = QTY_DIGITS) -> float:
    return float(round(x, d))


def at(monday: pd.Timestamp, day: int) -> pd.Timestamp:
    return monday + pd.Timedelta(days=day) + NOON


def mondays(start: str, end: str) -> pd.DatetimeIndex:
    """Monday of every full week from the week of ``start`` to the week ending by ``end``."""
    s = pd.Timestamp(start)
    s = s - pd.Timedelta(days=s.weekday())
    e = pd.Timestamp(end)
    last = e - pd.Timedelta(days=(e.weekday() + 1) % 7)       # the Sunday on or before end
    return pd.date_range(s, last - pd.Timedelta(days=6), freq="7D")


def price_at(prices: pd.DataFrame, item: str, when: pd.Timestamp) -> Tuple[float, bool]:
    """Latest monthly price at or before ``when``; flag if it is carried past the data."""
    s = prices[item].dropna()
    s = s[s.index <= when]
    if s.empty:
        raise ValueError(f"no {item} price on or before {when.date()}")
    stale = (when - s.index[-1]).days > 62
    return float(s.iloc[-1]), stale


# ---------------------------------------------------------------------------
# costs and prices
# ---------------------------------------------------------------------------


def supplier_index(cfg: ProductConfig, supplier: str) -> float:
    return cfg.suppliers[supplier].quote.price_index


def target_prices(cfg: ProductConfig, prices: pd.DataFrame, when: pd.Timestamp) -> Dict[str, float]:
    """Should-cost target per quoted item at ``when`` (cited index where linked)."""
    latest = {c: price_at(prices, c, when)[0] for c in prices.columns}
    return src_mod.should_cost(cfg, latest)["target_price_usd"].to_dict()


def cost_at(cfg: ProductConfig, prices: pd.DataFrame, vendor_of: Dict[str, str], per_unit: Dict[str, Dict[str, float]],
            root: str, mid: str, when: pd.Timestamp) -> Dict[str, float]:
    """Cost per item at the prices of ``when``: awarded supplier's quote on the should-cost
    target for purchased items; ``mid`` carries its material only; ``root`` adds conversion."""
    tp = target_prices(cfg, prices, when)
    c = {i: tp[i] * supplier_index(cfg, s) for i, s in vendor_of.items()}
    c[mid] = sum(q * c[x] for x, q in per_unit[mid].items())
    c[f"{root}:material"] = sum(q * c[x] for x, q in per_unit[root].items())
    c[root] = c[f"{root}:material"] + cfg.history.conversion_usd_per_kg
    return c


def standards(cfg: ProductConfig, prices: pd.DataFrame, vendor_of: Dict[str, str], years: List[int],
              per_unit: Dict[str, Dict[str, float]], root: str, mid: str) -> pd.DataFrame:
    """Standard cost per item and year, rolled each January from the prior December's prices."""
    rows = []
    for y in years:
        for i, v in cost_at(cfg, prices, vendor_of, per_unit, root, mid, pd.Timestamp(f"{y - 1}-12-01")).items():
            rows.append({"year": y, "item": i, "std_usd_per_uom": v})
    return pd.DataFrame(rows)


def list_prices(cfg: ProductConfig, prices: pd.DataFrame, vendor_of: Dict[str, str],
                per_unit: Dict[str, Dict[str, float]], root: str, mid: str,
                start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """The finished item's list price, reset every ``reprice_every_months`` from the prior
    month's input costs: cost / (1 - target margin), in cents. Customers pay it less their
    discount. Costs move with corn and the producer price indices, so prices do too."""
    h = cfg.history
    step = h.reprice_every_months
    first = pd.Timestamp(year=start.year, month=1, day=1)
    while first + pd.DateOffset(months=step) <= start:
        first += pd.DateOffset(months=step)
    rows, m = [], first
    while m <= end:
        c = cost_at(cfg, prices, vendor_of, per_unit, root, mid, m - pd.DateOffset(months=1))
        rows.append({"valid_from": m, "list_price": round(c[root] / (1 - h.gross_margin), 2),
                     "cost_basis": c[root]})
        m += pd.DateOffset(months=step)
    return pd.DataFrame(rows)


def list_price_on(table: pd.DataFrame, when: pd.Timestamp) -> float:
    return float(table[table["valid_from"] <= when]["list_price"].iloc[-1])


# ---------------------------------------------------------------------------
# the simulation
# ---------------------------------------------------------------------------


def _bom_per_batch(cfg: ProductConfig, parent: str) -> Tuple[float, Dict[str, float]]:
    """Batch size and component quantities per batch, rounded as the ERP BOM stores them."""
    base = _round(cfg.items[parent].batch_size or 1.0)
    comps = {b.component: _round(b.qty_per * (cfg.items[parent].batch_size or 1.0))
             for b in cfg.bom if b.parent == parent}
    return base, comps


def max_batches_per_week(cfg: ProductConfig, mid: str, batch: float) -> Tuple[int, float]:
    """Whole batches the constraining resource can run in a week, and the exact rate."""
    rate = math.inf
    for line in cfg.bill_of_resources:
        if line.item != mid:
            continue
        res = cfg.resources[line.resource]
        rate = min(rate, res.units * res.hours_per_week * res.availability / (line.hours_per_unit * batch))
    if not math.isfinite(rate):
        raise ValueError(f"{mid}: no bill-of-resources line, so no capacity limit")
    return int(math.floor(rate)), rate


def simulate(cfg: ProductConfig, prices: pd.DataFrame, quotes: pd.DataFrame, awards: pd.DataFrame) -> History:
    h = cfg.history
    if h is None:
        raise ValueError("config has no history section")
    root = cfg.demand.item
    makes = [b.component for b in cfg.bom if b.parent == root and cfg.items[b.component].type != "purchased"]
    if len(makes) != 1:
        raise ValueError(f"history expects one made intermediate under {root}; found {makes}")
    mid = makes[0]
    weeks = mondays(h.start, h.end)
    T = len(weeks)
    end = weeks[-1] + pd.Timedelta(days=6)
    lead = h.order_lead_weeks

    mid_batch, mid_comps = _bom_per_batch(cfg, mid)
    root_batch, root_comps = _bom_per_batch(cfg, root)
    per_unit = {mid: {c: q / mid_batch for c, q in mid_comps.items()},
                root: {c: q / root_batch for c, q in root_comps.items() if c != mid}}
    per_unit[root][mid] = root_comps[mid] / root_batch
    cap, cap_rate = max_batches_per_week(cfg, mid, mid_batch)
    purchased = [c for c in list(mid_comps) + list(root_comps) if cfg.items[c].type == "purchased"]
    vendor_of = {i: awards.loc[i, "awarded_to"] for i in purchased}
    years = list(range(weeks[0].year - 1, end.year + 1))
    std = standards(cfg, prices, vendor_of, years, per_unit, root, mid)
    stdv = {(r.year, r.item): r.std_usd_per_uom for r in std.itertuples()}
    notes: List[str] = []

    # ---- demand and forecast (weekly, with room for orders placed ahead) ----
    extra = lead + max(p.every_weeks for p in h.customers.values())
    index = demand_mod.periods(weeks[0].strftime("%Y-%m-%d"), T + extra, cfg.freq)
    dem = demand_mod.generate(cfg.demand, index, anchor=cfg.start, seed=h.seed)["qty"].to_numpy()
    fc = demand_mod.generate(replace(cfg.demand, noise_cv=0.0), index, anchor=cfg.start)["qty"].to_numpy()
    week_of = {w: t for t, w in enumerate(pd.date_range(weeks[0], periods=T + extra, freq="7D"))}

    def wk(date: str) -> int:
        d = pd.Timestamp(date)
        return week_of[d - pd.Timedelta(days=d.weekday())]

    ev_rows = []
    spike = {c: np.zeros(T + extra) for c in h.customers}
    contamination_weeks: List[int] = []
    outages: List[Tuple[str, str, int, int]] = []       # supplier, item, first week, end week (excl.)
    for e in h.events:
        s = wk(e.start)
        if e.kind == "demand_spike":
            spike[e.target][s:s + e.weeks] = e.size
        elif e.kind == "contamination":
            contamination_weeks += [s] * int(e.size or 1)
        elif e.kind == "supplier_outage":
            outages.append((e.target, e.item, s, s + e.weeks))
        ev_rows.append({"kind": e.kind, "start": weeks[s] if s < T else pd.NaT, "weeks": e.weeks,
                        "size": e.size, "target": e.target, "item": e.item, "note": e.note})

    # ---- the order book: every order placed by the end of the history ----
    bag = None
    for c in root_comps:
        if cfg.items[c].uom == "unit" and cfg.items[c].category == "packaging":
            bag = round(root_batch / root_comps[c], 2)            # kg of powder per bag
    plist = list_prices(cfg, prices, vendor_of, per_unit, root, mid,
                        weeks[0] - pd.Timedelta(weeks=lead), end)
    orders = []
    customer_dem = np.zeros(T + extra)
    for k, (cid, p) in enumerate(h.customers.items()):
        offset = k % p.every_weeks
        for due in range(offset, T + lead, p.every_weeks):
            span = range(due, min(due + p.every_weeks, T + extra))
            raw = sum(p.share * dem[d] * (1 + spike[cid][d]) for d in span)
            for d in span:
                customer_dem[d] += p.share * dem[d] * (1 + spike[cid][d])
            qty = round(raw / bag) * bag if bag else round(raw)
            placed = pd.Timestamp(weeks[0]) + pd.Timedelta(weeks=due - lead)
            if due - lead > T - 1 or qty <= 0:
                continue
            due_monday = weeks[0] + pd.Timedelta(weeks=due)
            orders.append({
                "key": f"hist:so:{cid}:{due_monday.date()}", "customer": cid, "due_week": due,
                "date_order": at(placed, ORDER_DAY), "date_promised": at(due_monday, SHIP_DAY),
                "qty": float(qty), "list_price": list_price_on(plist, placed),
                "price_unit": round(list_price_on(plist, placed) * (1 - p.discount), 2),
                "spike": bool(spike[cid][due] > 0),
            })
    orders.sort(key=lambda o: (o["due_week"], o["key"]))

    # ---- simulation state ----
    opening = {i: float(cfg.items[i].planning.on_hand) for i in [root, mid] + purchased}
    stock = dict(opening)
    flows = []
    batches: List[dict] = []
    waiting_mid: List[dict] = []         # finished intermediate batches not yet converted
    pos: List[dict] = []                 # purchase orders (one per supplier and week)
    rng_po = np.random.default_rng([h.seed, 2])
    rng_pay = np.random.default_rng([h.seed, 3])
    rng_drift = np.random.default_rng([h.seed, 4])
    quote = {(q.item, q.supplier): q for q in quotes.itertuples()}
    runner_up = {i: quotes[(quotes["item"] == i) & (quotes["rank"] == 2)]["supplier"].iloc[0]
                 for i in purchased if len(quotes[quotes["item"] == i]) > 1}
    unshipped = list(orders)
    kpi = []

    def outage(supplier: str, item: str, t: int) -> Optional[Tuple[int, int]]:
        for s, i, a, b in outages:
            if s == supplier and i == item and a <= t < b:
                return a, b
        return None

    for t, monday in enumerate(weeks):
        f = {i: {"opening": stock[i], "received": 0.0, "produced": 0.0, "consumed": 0.0, "shipped": 0.0,
                 "scrapped": 0.0} for i in stock}

        # 1. receipts due this week
        for po in pos:
            if po["arrival_week"] == t:
                for ln in po["lines"]:
                    ln["qty_received"] = _round(ln["qty"] * po["fill"])
                    stock[ln["item"]] += ln["qty_received"]
                    f[ln["item"]]["received"] += ln["qty_received"]
                po["date_received"] = at(monday, RECEIPT_DAY)

        # 2. convert last week's intermediate batches (if packaging is on hand)
        root_out = 0.0
        still = []
        for b in waiting_mid:
            if all(stock[c] + 1e-9 >= q for c, q in root_comps.items()):
                for c, q in root_comps.items():
                    stock[c] -= q
                    f[c]["consumed"] += q
                root_out += root_batch
                batches.append({"key": f"hist:mo:{root}:{b['batch']}", "product": root, "batch": b["batch"],
                                "qty": root_batch, "date_start": at(monday, 0), "date_finished": at(monday, PWD_DONE_DAY),
                                "week": t, "scrapped": False, "consumes": dict(root_comps)})
            else:
                still.append(b)
        waiting_mid = still

        # 3. ship whole orders, first due first, from powder made in earlier weeks
        shipped = on_time = due_qty = 0.0
        for o in list(unshipped):
            if o["due_week"] > t:
                break
            if stock[root] + 1e-9 < o["qty"]:
                break                                   # first-in-line waits; nothing jumps the queue
            stock[root] -= o["qty"]
            f[root]["shipped"] += o["qty"]
            o["ship_week"], o["date_shipped"] = t, at(monday, SHIP_DAY)
            shipped += o["qty"]
            on_time += o["qty"] if t == o["due_week"] else 0.0
            unshipped.remove(o)
        due_now = [o for o in orders if o["due_week"] == t]
        due_qty = sum(o["qty"] for o in due_now)

        # 4. start fermentation batches: cover safety stock after the booked orders
        booked = sum(o["qty"] for o in unshipped if o["due_week"] <= t + 2)
        ss = cfg.items[root].planning.safety_stock
        need = ss + booked - (stock[root] + root_out)
        n = max(0, min(cap, math.ceil(need / root_batch - 1e-9)))
        for c, q in mid_comps.items():
            n = min(n, int((stock[c] + 1e-9) // q))
        scrapped = 0
        mid_out = 0.0
        for j in range(n):
            for c, q in mid_comps.items():
                stock[c] -= q
                f[c]["consumed"] += q
            bid = f"{monday.date()}-{j + 1}"
            # a contamination hits the first batch(es) started on or after its week
            lost = any(w <= t for w in contamination_weeks)
            if lost:
                contamination_weeks.remove(min(contamination_weeks))
            batches.append({"key": f"hist:mo:{mid}:{bid}", "product": mid, "batch": bid, "qty": mid_batch,
                            "date_start": at(monday, 0), "date_finished": at(monday, FERM_DONE_DAY), "week": t,
                            "scrapped": lost, "consumes": dict(mid_comps)})
            f[mid]["produced"] += mid_batch
            mid_out += mid_batch
            if lost:
                f[mid]["scrapped"] += mid_batch
                scrapped += 1
            else:
                waiting_mid.append({"batch": bid})

        # 5. purchasing: reorder point per item, one PO per supplier and week
        horizon = fc[t + 1:t + 5]
        rate = float(horizon.mean()) / root_batch if len(horizon) else n
        new_lines: Dict[str, List[dict]] = {}
        for i in purchased:
            per_batch = mid_comps.get(i, 0.0) + root_comps.get(i, 0.0)
            use = rate * per_batch
            sup = vendor_of[i]
            if outage(sup, i, t) and i in runner_up:
                sup = runner_up[i]
            q = quote[(i, sup)]
            L = int(q.lead_time_weeks)
            open_qty = sum(ln["qty"] for po in pos if po["arrival_week"] > t - 1 and "date_received" not in po
                           for ln in po["lines"] if ln["item"] == i and not outage(po["supplier"], i, t))
            projected = stock[i] + open_qty - use * (L + 1)
            safety = max(cfg.items[i].planning.safety_stock, h.safety_cover_weeks * use)
            if projected >= safety:
                continue
            qty = max(max(h.min_cover_weeks, cfg.suppliers[sup].quote.moq_weeks) * use, safety - projected)
            lot = cfg.items[i].planning.lot_sizing
            if lot.rule == "fixed_order_quantity" and lot.quantity > 0:
                qty = math.ceil(qty / lot.quantity) * lot.quantity
            elif cfg.items[i].uom == "unit":
                qty = math.ceil(qty)
            new_lines.setdefault(sup, []).append({"item": i, "qty": _round(qty), "lead": L})
        for sup, lines in new_lines.items():
            L = max(ln["lead"] for ln in lines)
            q = cfg.suppliers[sup].quote
            on_rate = min(1.0, q.otif / (1 - q.short_ship_rate)) if q.short_ship_rate < 1 else 0.0
            late = 0 if rng_po.random() < on_rate else max(1, math.ceil(abs(rng_po.normal(0, q.lead_time_sigma))))
            fill = 1.0 if rng_po.random() >= q.short_ship_rate else cfg.sourcing.short_ship_fraction
            arrival = t + L + late
            for ln in lines:
                o = outage(sup, ln["item"], min(arrival, T - 1))
                if o and arrival < o[1]:
                    arrival = o[1]
                    late = arrival - t - L
            for ln in lines:
                indexed = ln["item"] in prices.columns
                tp = target_prices(cfg, prices, monday)[ln["item"]]
                price = tp * q.price_index
                if not indexed:
                    price *= 1 + cfg.sourcing.price_drift_cv * rng_drift.standard_normal()
                ln["price_unit"] = _round(price, PRICE_DIGITS)
                ln["std"] = stdv[(monday.year, ln["item"])]
                if indexed and price_at(prices, ln["item"], monday)[1]:
                    notes.append(f"{ln['item']}: price carried forward from the last published month "
                                 f"(from {monday.date()})")
            pos.append({"key": f"hist:po:{sup}:{monday.date()}", "supplier": sup, "week": t,
                        "date_order": at(monday, ORDER_DAY), "promised_week": t + L,
                        "date_promised": at(monday + pd.Timedelta(weeks=L), RECEIPT_DAY),
                        "arrival_week": arrival, "weeks_late": late, "fill": fill,
                        "emergency": sup != vendor_of[lines[0]["item"]], "lines": lines})

        # 6. end of week: this week's output becomes available next week
        stock[root] += root_out
        f[root]["produced"] += root_out
        stock[mid] += mid_out - scrapped * mid_batch     # a lost batch is made, then scrapped
        for i in stock:
            f[i]["closing"] = stock[i]
            if stock[i] < -1e-6:
                raise AssertionError(f"{i} negative in week {monday.date()}: {stock[i]}")
            flows.append({"week": monday, "item": i, **f[i]})
        late_backlog = sum(o["qty"] for o in unshipped if o["due_week"] <= t)
        y = monday.year
        kpi.append({
            "week": monday, "demand": customer_dem[t], "forecast": fc[t], "orders_due_qty": due_qty,
            "shipped_qty": shipped, "shipped_on_time_qty": on_time, "past_due_qty": late_backlog,
            "orders_due": len(due_now),
            "orders_on_time": sum(1 for o in due_now if o.get("ship_week") == t),
            "batches_started": n, "batches_scrapped": scrapped, "batch_capacity": cap_rate,
            "utilisation": n / cap_rate,
            "revenue": sum(o["qty"] * o["price_unit"] for o in orders if o.get("ship_week") == t),
            "cogs_std": shipped * stdv[(y, root)],
            "inventory_value_std": sum(stock[i] * stdv[(y, i)] for i in stock),
            **{f"stock_{i}": stock[i] for i in stock},
        })

    # ---- documents ----
    def pay_date(start: pd.Timestamp, days: float, cv: float) -> pd.Timestamp:
        d = max(1, int(round(days * (1 + cv * rng_pay.standard_normal()))))
        return (start + pd.Timedelta(days=d)).normalize() + NOON

    sales = pd.DataFrame(orders)
    for col in ("ship_week", "date_shipped"):
        if col not in sales:
            sales[col] = None
    sales["invoice_date"] = sales["date_shipped"].map(lambda d: d.normalize() if isinstance(d, pd.Timestamp) else pd.NaT)
    sales["invoice_due"] = sales["invoice_date"] + pd.Timedelta(days=h.customer_terms_days)
    pay = []
    for r in sales.itertuples():
        if pd.isna(r.invoice_date):
            pay.append(pd.NaT)
            continue
        d = pay_date(r.invoice_date, h.customers[r.customer].pay_days, h.pay_days_cv)
        pay.append(d if d <= end + NOON else pd.NaT)
    sales["date_paid"] = pay
    sales["amount"] = sales["qty"] * sales["price_unit"]

    plines = []
    for po in pos:
        if po["date_order"] > end + NOON:
            continue
        received = "date_received" in po
        bill = po["date_received"].normalize() if received else pd.NaT
        paid = bill + pd.Timedelta(days=h.vendor_terms_days) + NOON if received else pd.NaT
        if received and paid > end + NOON:
            paid = pd.NaT
        for ln in po["lines"]:
            plines.append({
                "key": po["key"], "supplier": po["supplier"], "item": ln["item"], "qty": ln["qty"],
                "qty_received": ln.get("qty_received", 0.0), "price_unit": ln["price_unit"], "std_usd_per_uom": ln["std"],
                "date_order": po["date_order"], "date_promised": po["date_promised"], "promised_week": po["promised_week"],
                "arrival_week": po["arrival_week"] if received else None, "weeks_late": po["weeks_late"] if received else None,
                "date_received": po.get("date_received", pd.NaT), "bill_date": bill,
                "bill_due": bill + pd.Timedelta(days=h.vendor_terms_days) if received else pd.NaT,
                "date_paid": paid, "short": po["fill"] < 1 and received, "emergency": po["emergency"],
            })
    purchases = pd.DataFrame(plines)
    purchases["ppv_usd"] = (purchases["price_unit"] - purchases["std_usd_per_uom"]) * purchases["qty_received"]

    production = pd.DataFrame(batches).sort_values(["date_start", "product", "batch"], ascending=[True, False, True])
    kpis = pd.DataFrame(kpi)
    rec = purchases.dropna(subset=["arrival_week"])
    rec = rec.assign(week=[weeks[int(a)] for a in rec["arrival_week"]], value=rec["qty_received"] * rec["price_unit"])
    by_week = rec.groupby("week")
    kpis = kpis.merge(by_week["value"].sum().rename("purchases_received_usd"), left_on="week", right_index=True, how="left")
    kpis = kpis.merge(by_week["ppv_usd"].sum().rename("ppv_usd"), left_on="week", right_index=True, how="left")
    kpis[["purchases_received_usd", "ppv_usd"]] = kpis[["purchases_received_usd", "ppv_usd"]].fillna(0.0)
    return History(weeks=weeks, sales=sales, purchases=purchases, production=production.reset_index(drop=True),
                   flows=pd.DataFrame(flows), standards=std, price_list=plist, kpis=kpis, events=pd.DataFrame(ev_rows),
                   opening=opening, notes=_first_per_item(notes))


def _first_per_item(notes: List[str]) -> List[str]:
    seen: Dict[str, str] = {}
    for n in notes:
        seen.setdefault(n.split(":", 1)[0], n)
    return sorted(seen.values())


def conservation_errors(hist: History, tol: float = 1e-6) -> List[str]:
    """Rows where opening + received + produced - consumed - shipped - scrapped != closing."""
    f = hist.flows
    calc = f["opening"] + f["received"] + f["produced"] - f["consumed"] - f["shipped"] - f["scrapped"]
    bad = f[(calc - f["closing"]).abs() > tol]
    return [f"{r.week.date()} {r.item}: off by {c - r.closing:g}" for r, c in zip(bad.itertuples(), calc[bad.index])]
