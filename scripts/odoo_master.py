"""Load master data from a product config into the live Odoo database (ADR 0017).

    .venv/bin/python scripts/odoo_master.py products/blg_whey_protein.yaml               # create missing, show diffs
    .venv/bin/python scripts/odoo_master.py products/blg_whey_protein.yaml --apply-diffs # also apply the diffs shown

Master data = units (batch and lot sizes), partners (bidding suppliers and customers),
products, vendor price lists, bills of materials, reorder rules. Transactions (stock,
orders, invoices) are not created here.

Rules, as decided for the system of record:
- every record is written through ``Odoo.ensure()``: created once with a stable
  ``x_pps_key`` and returned untouched on reruns;
- when an existing record differs from the config (e.g. it was edited in the UI), the
  difference is **shown and nothing is changed**. ``--apply-diffs`` writes the shown
  values, and only ever on records that carry a ``x_pps_key`` (never on hand-made ones);
- reorder rules are created with the **manual** trigger: the planner runs replenishment.

The planner (``plan``) is pure and tested offline; ``apply`` talks to Odoo.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import Odoo, OdooError, pending_changes  # noqa: E402
from odoo_seed import UOM_XMLID, supplier_prices  # noqa: E402
from ppsim import bom as bom_mod  # noqa: E402

# "Product Unit" precision set by the live bootstrap: Odoo stores quantities to 4 decimals,
# so differences smaller than half a unit in the 4th decimal are rounding, not edits.
FLOAT_TOL = 0.5e-4
ROUTE_XMLID = {"make": "mrp.route_warehouse0_manufacture", "buy": "purchase_stock.route_warehouse0_buy"}
STOCK_XMLID = "stock.stock_location_stock"


@dataclass(frozen=True)
class Ref:
    """Id of another planned record, resolved at apply time."""
    model: str
    key: str


@dataclass(frozen=True)
class XRef:
    """Id of a built-in Odoo record by xml id (via the bootstrap's refs file)."""
    xmlid: str


@dataclass(frozen=True)
class Variant:
    """The product.product of a planned product.template."""
    template_key: str


@dataclass
class Spec:
    model: str
    key: str
    vals: Dict[str, Any]
    compare: Tuple[str, ...] = ()      # fields diffed on an existing record
    note: str = ""


@dataclass
class Report:
    created: List[Spec] = field(default_factory=list)
    unchanged: List[Spec] = field(default_factory=list)
    diffs: List[Tuple[Spec, int, Dict[str, tuple]]] = field(default_factory=list)
    applied: List[Tuple[Spec, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# plan (pure)
# ---------------------------------------------------------------------------


def plan(cfg, res, days_per_week: float, trigger: str = "manual",
         costs: Optional[Dict[str, float]] = None, list_price: Optional[float] = None,
         levels=None) -> List[Spec]:
    """Ordered master-data specs for the config: dependencies always come first.

    ``costs`` (standard cost per item) and ``list_price`` (the finished item's selling
    price), when given, are set on the products and diffed like any other field.
    ``levels`` (``supplier_perf.reorder_levels``) sets kanban min/max on purchased items;
    without it, min = max = the planning safety stock.
    """
    costs = costs or {}
    root = cfg.demand.item
    planned = bom_mod.reachable(root, cfg.bom)
    lines = [b for b in cfg.bom if b.parent in planned]
    purchased = [i for i in planned if cfg.items[i].type == "purchased"]
    specs: List[Spec] = []

    # units: one batch / lot unit per item whose lot sizing needs it
    lot_uom: Dict[str, str] = {}
    for iid in planned:
        it = cfg.items[iid]
        lot = it.planning.lot_sizing
        if lot.rule == "fixed_order_quantity":
            name, factor = f"{iid} lot ({lot.quantity:,.0f} {it.uom})", lot.quantity
        elif lot.multiple > 1:
            name, factor = f"{iid} batch ({lot.multiple:,.0f} {it.uom})", lot.multiple
        else:
            continue
        key = f"uom:{iid}"
        lot_uom[iid] = key
        specs.append(Spec("uom.uom", key, {"name": name, "relative_uom_id": XRef(UOM_XMLID[it.uom]),
                                           "relative_factor": factor},
                          compare=("name", "relative_factor")))

    # partners: the supplier master (or the M3 vendor list) and the customers
    bidders = cfg.suppliers or cfg.vendors
    for p in bidders.values():
        specs.append(Spec("res.partner", f"partner:{p.id}", {"name": p.name, "is_company": True, "supplier_rank": 1},
                          compare=("name",)))
    for p in cfg.customers.values():
        specs.append(Spec("res.partner", f"partner:{p.id}", {"name": p.name, "is_company": True, "customer_rank": 1},
                          compare=("name",)))

    # products
    for iid in planned:
        it = cfg.items[iid]
        if it.uom not in UOM_XMLID:
            raise ValueError(f"{iid}: unsupported uom {it.uom!r}")
        buy = it.type == "purchased"
        vals = {
            "name": it.name, "default_code": iid, "type": "consu", "is_storable": True,
            "uom_id": XRef(UOM_XMLID[it.uom]), "sale_ok": it.type == "finished", "purchase_ok": buy,
            "route_ids": [[6, 0, [XRef(ROUTE_XMLID["buy" if buy else "make"])]]],
        }
        compare = ["name", "default_code", "uom_id", "sale_ok", "purchase_ok"]
        if iid in costs:
            vals["standard_price"] = round(costs[iid], 4)
            compare.append("standard_price")
        if list_price is not None and it.type == "finished":
            vals["list_price"] = list_price
            compare.append("list_price")
        specs.append(Spec("product.template", f"product:{iid}", vals, compare=tuple(compare)))

    # vendor price lists: every bidder, the awarded supplier at sequence 1
    vendor_of = ({i: r["awarded_to"] for i, r in res.awards.iterrows()} if res.awards is not None
                 else {i: v.id for v in bidders.values() for i in v.supplies})
    quoted = supplier_prices(cfg, res, days_per_week, purchased)
    for iid, sid, vals in quoted:
        specs.append(Spec("product.supplierinfo", f"supplierinfo:{iid}:{sid}", {
            "partner_id": Ref("res.partner", f"partner:{sid}"),
            "product_tmpl_id": Ref("product.template", f"product:{iid}"), **vals,
        }, compare=("price", "min_qty", "delay", "sequence")))
    for iid in purchased:
        if any(q[0] == iid for q in quoted):
            continue
        if iid not in vendor_of:
            raise ValueError(f"{iid}: no vendor supplies this purchased item")
        lot = cfg.items[iid].planning.lot_sizing
        sid = vendor_of[iid]
        specs.append(Spec("product.supplierinfo", f"supplierinfo:{iid}:{sid}", {
            "partner_id": Ref("res.partner", f"partner:{sid}"),
            "product_tmpl_id": Ref("product.template", f"product:{iid}"),
            "min_qty": lot.quantity if lot.rule == "fixed_order_quantity" else lot.minimum,
            "delay": int(cfg.items[iid].planning.lead_time * days_per_week),
        }, compare=("min_qty", "delay")))

    # bills of materials: one per manufactured item, per batch
    for parent in [i for i in planned if cfg.items[i].type != "purchased"]:
        it = cfg.items[parent]
        base = it.batch_size or 1.0
        comps = [b for b in lines if b.parent == parent]
        specs.append(Spec("mrp.bom", f"bom:{parent}", {
            "product_tmpl_id": Ref("product.template", f"product:{parent}"),
            "product_qty": base, "product_uom_id": XRef(UOM_XMLID[it.uom]), "type": "normal",
            "produce_delay": int(it.planning.lead_time * days_per_week),
            "bom_line_ids": [[0, 0, {
                "product_id": Variant(f"product:{b.component}"),
                "product_qty": round(b.qty_per * base, 4),
                "product_uom_id": XRef(UOM_XMLID[cfg.items[b.component].uom]),
            }] for b in comps],
        }, compare=("product_qty", "produce_delay"),
            note="component lines are set on creation; later line edits are not diffed"))

    # reorder rules: kanban min/max for purchased items when given, else min = max = safety stock
    for iid in planned:
        ss = cfg.items[iid].planning.safety_stock
        lo, hi = ss, ss
        if levels is not None and iid in levels.index:
            lo, hi = float(levels.loc[iid, "min_qty"]), float(levels.loc[iid, "max_qty"])
        vals: Dict[str, Any] = {"product_id": Variant(f"product:{iid}"), "location_id": XRef(STOCK_XMLID),
                                "product_min_qty": lo, "product_max_qty": hi, "trigger": trigger}
        if iid in lot_uom:
            vals["replenishment_uom_id"] = Ref("uom.uom", lot_uom[iid])
        specs.append(Spec("stock.warehouse.orderpoint", f"orderpoint:{iid}", vals,
                          compare=("product_min_qty", "product_max_qty", "trigger", "replenishment_uom_id")))
    return specs


# ---------------------------------------------------------------------------
# apply (talks to Odoo)
# ---------------------------------------------------------------------------


def resolve(value: Any, ids: Dict[str, int], variants: Dict[str, int], o: Odoo) -> Any:
    if isinstance(value, Ref):
        if value.key not in ids:
            raise OdooError(f"unresolved reference {value.model}:{value.key} (planned out of order?)")
        return ids[value.key]
    if isinstance(value, Variant):
        if value.template_key not in variants:
            raise OdooError(f"no product variant for {value.template_key}")
        return variants[value.template_key]
    if isinstance(value, XRef):
        return o.ref(value.xmlid)
    if isinstance(value, dict):
        return {k: resolve(v, ids, variants, o) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [resolve(v, ids, variants, o) for v in value]
    return value


def apply(o: Odoo, specs: Sequence[Spec], apply_diffs: bool = False) -> Report:
    report = Report()
    ids: Dict[str, int] = {}
    variants: Dict[str, int] = {}
    for spec in specs:
        vals = resolve(spec.vals, ids, variants, o)
        rid, created = o.ensure(spec.model, spec.key, vals)
        ids[spec.key] = rid
        if spec.model == "product.template":
            rows = o.search_read("product.product", [["product_tmpl_id", "=", rid]], ["id"], limit=1)
            if not rows:
                raise OdooError(f"{spec.key}: template {rid} has no variant")
            variants[spec.key] = rows[0]["id"]
        if created:
            report.created.append(spec)
            continue
        if not spec.compare:
            report.unchanged.append(spec)
            continue
        current = o.search_read(spec.model, [["id", "=", rid]], list(spec.compare))[0]
        diff = pending_changes(current, {f: vals[f] for f in spec.compare if f in vals}, float_tol=FLOAT_TOL)
        if not diff:
            report.unchanged.append(spec)
            continue
        report.diffs.append((spec, rid, diff))
        if apply_diffs:
            o.write(spec.model, [rid], {f: new for f, (_, new) in diff.items()})
            report.applied.append((spec, rid))
    return report


def print_report(report: Report, apply_diffs: bool) -> None:
    by_model: Dict[str, List[int]] = {}
    for s in report.created + report.unchanged + [d[0] for d in report.diffs]:
        by_model.setdefault(s.model, [0, 0, 0])
    for s in report.created:
        by_model[s.model][0] += 1
    for s in report.unchanged:
        by_model[s.model][1] += 1
    for s, _, _ in report.diffs:
        by_model[s.model][2] += 1
    print(f"{'model':30s} {'created':>8s} {'unchanged':>10s} {'differs':>8s}")
    for m, (c, u, d) in by_model.items():
        print(f"{m:30s} {c:8d} {u:10d} {d:8d}")
    if report.diffs:
        verb = "APPLIED" if apply_diffs else "NOT applied (rerun with --apply-diffs to write the config values)"
        print(f"\n{len(report.diffs)} record(s) differ from the config, {verb}:")
        for spec, rid, diff in report.diffs:
            for f, (have, want) in diff.items():
                print(f"  {spec.key:32s} {f}: Odoo has {have!r}, config says {want!r}")


def current_costs(cfg, res, year: Optional[int] = None) -> Tuple[Dict[str, float], Optional[float]]:
    """This year's standard costs and selling price (ADR 0018), or nothing without prices."""
    if cfg.history is None or res.prices is None or res.awards is None:
        return {}, None
    import datetime as dt

    import pandas as pd

    from ppsim import history as H
    y = year or dt.date.today().year
    root = cfg.demand.item
    mid = next(b.component for b in cfg.bom if b.parent == root and cfg.items[b.component].type != "purchased")
    _, mid_comps = H._bom_per_batch(cfg, mid)
    root_batch, root_comps = H._bom_per_batch(cfg, root)
    mid_batch = H._round(cfg.items[mid].batch_size)
    per_unit = {mid: {c: q / mid_batch for c, q in mid_comps.items()},
                root: {c: q / root_batch for c, q in root_comps.items()}}
    purchased = [c for c in list(mid_comps) + list(root_comps) if cfg.items[c].type == "purchased"]
    vendor_of = {i: res.awards.loc[i, "awarded_to"] for i in purchased}
    prices = res.prices.join(res.index_prices, how="outer") if res.index_prices is not None else res.prices
    std = H.standards(cfg, prices, vendor_of, [y], per_unit, root, mid)
    vals = dict(zip(std["item"], std["std_usd_per_uom"]))
    today = pd.Timestamp(dt.date.today())
    plist = H.list_prices(cfg, prices, vendor_of, per_unit, root, mid, today, today)
    return {i: v for i, v in vals.items() if i in cfg.items}, H.list_price_on(plist, today)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    ap.add_argument("--apply-diffs", action="store_true", help="write config values over the differences shown")
    ap.add_argument("--trigger", choices=("manual", "auto"), default="manual", help="reorder-rule trigger")
    args = ap.parse_args(argv)

    from ppsim.config import load_config
    from ppsim.pipeline import run
    from ppsim.registry import load_registry

    cfg = load_config(args.config)
    res = run(cfg)        # cited FRED prices (cached); without them should-cost falls back to mock bases
    if res.prices is None:
        print("warning: no FRED prices; vendor prices use the mock fallback bases", file=sys.stderr)
    days_per_week = load_registry(ROOT / "knowledge" / "assumptions.csv")["days_per_week"].value
    costs, asp = current_costs(cfg, res)
    from ppsim.supplier_perf import reorder_levels
    levels = reorder_levels(cfg, res.quotes, res.awards, res.usage) if res.awards is not None else None
    specs = plan(cfg, res, days_per_week, trigger=args.trigger, costs=costs, list_price=asp, levels=levels)
    o = Odoo.live()
    print(f"{o.db}: {len(specs)} master-data records planned from {args.config}")
    report = apply(o, specs, apply_diffs=args.apply_diffs)
    print_report(report, args.apply_diffs)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
