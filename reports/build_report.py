"""Build the static HTML report for a product config.

    .venv/bin/python reports/build_report.py products/blg_whey_protein.yaml [--offline]

Writes outputs/report/index.html (gitignored: it embeds IMF-derived price series,
which aren't redistributed; see ADR 0003). The page is self-contained: inline CSS,
JS and data, no server needed. Charts follow the repo's dataviz rules: one y-axis per
chart, a legend for 2+ series, hover tooltips, a table view per chart, light/dark themes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ppsim.pipeline import run  # noqa: E402

TEMPLATE = Path(__file__).with_name("template.html")
OUT = ROOT / "outputs" / "report" / "index.html"
IMF = "Source: International Monetary Fund, retrieved from FRED, Federal Reserve Bank of St. Louis (PMAIZMTUSDM, PSUGAISAUSDM)."


def vals(a) -> list:
    return [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), 4) for v in np.asarray(a, dtype=float)]


def week_short(label: str) -> str:
    start = pd.Timestamp(label.split("/")[0])
    return start.strftime("%b %d")


def short_name(name: str) -> str:
    """Chart labels: drop the "(fictional)" marker, which the subtitle already states."""
    return name.replace(" (fictional)", "")


def money(v: float) -> str:
    return f"${v / 1e6:,.2f}M" if abs(v) >= 1e5 else f"${v:,.0f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    ap.add_argument("--offline", action="store_true", help="use cached FRED data only")
    ap.add_argument("--out", type=Path, default=OUT, help="output HTML path")
    args = ap.parse_args(argv)

    res = run(args.config, offline=args.offline)
    cfg = res.cfg
    root = cfg.demand.item
    variants = {name: run(args.config, variant=name, offline=args.offline) for name in cfg.variants}

    rows = []
    tiles = []

    # ---- S&OP ------------------------------------------------------------
    if res.sop is not None:
        sop = res.sop
        months = list(sop.index)
        on_target = int((~sop["below_target"]).sum())
        tiles.append({
            "label": f"S&OP ({cfg.sop.strategy}), months at inventory target",
            "value": f"{on_target} / {len(sop)}",
            "status": ["good", "no stockouts"] if not sop["stockout"].any() else ["bad", "stockout months"],
            "note": f"utilization {sop['utilization'].min():.0%}–{sop['utilization'].max():.0%} of capacity",
        })
        rows.append([
            {"title": "S&OP: monthly production vs demand", "sub": f"{root}, kg per month · demand is MOCK · capacity from cited batch size, cycle and uptime × mock reactor count",
             "x": months, "xName": "Month", "unit": "kg",
             "series": [
                 {"name": "Demand (mock)", "kind": "bar", "slot": 2, "values": vals(sop["demand"])},
                 {"name": "Planned production", "kind": "bar", "slot": 1, "values": vals(sop["production"])},
                 {"name": "Capacity", "kind": "ref", "slot": "ref", "values": vals(sop["capacity"])},
             ]},
            {"title": "S&OP: ending inventory vs target", "sub": f"{root}, kg · target = {cfg.sop.target_cover_months:g} month(s) of next month's demand [mock policy]",
             "x": months, "xName": "Month", "unit": "kg",
             "series": [
                 {"name": "Ending inventory", "kind": "line", "slot": 1, "values": vals(sop["ending_inventory"])},
                 {"name": "Target", "kind": "ref", "slot": "ref", "values": vals(sop["target_inventory"])},
             ]},
        ])

    # ---- MPS -------------------------------------------------------------
    if res.mps is not None:
        t = res.mps.table
        weeks = list(t.columns)
        zones, z = [], res.mps.zones
        for name in ("frozen", "slushy"):
            idx = [i for i, v in enumerate(z) if v == name]
            if idx:
                zones.append({"from": idx[0], "to": idx[-1] + 1, "label": name})
        cap = [cfg.sop.capacity_per_week] * len(weeks) if cfg.sop and cfg.sop.capacity_per_week else None
        series = [
            {"name": "Firm (in progress)", "kind": "bar", "slot": 3, "values": vals(t.loc["firm_mps"])},
            {"name": "Planned MPS", "kind": "bar", "slot": 1, "values": vals(t.loc["planned_mps"])},
            {"name": "Projected demand", "kind": "line", "slot": 2, "values": vals(t.loc["projected_demand"])},
        ]
        if cap:
            series.append({"name": "Weekly capacity", "kind": "ref", "slot": "ref", "values": vals(cap)})
        rows.append([{
            "title": "MPS: weekly schedule vs demand", "sub": f"{root}, kg per week · shaded: frozen (orders only) and slushy (no new planned orders) zones",
            "x": weeks, "xShort": [week_short(w) for w in weeks], "xName": "Week", "unit": "kg", "stacked": True, "zones": zones,
            "series": series, "height": 260,
        }])
        ss = cfg.items[root].planning.safety_stock
        pab_row = [{
            "title": "Projected available balance", "sub": f"{root}, kg at week end",
            "x": weeks, "xShort": [week_short(w) for w in weeks], "xName": "Week", "unit": "kg",
            "series": [
                {"name": "Projected available balance", "kind": "line", "slot": 1, "values": vals(t.loc["projected_available_balance"])},
                {"name": "Safety stock", "kind": "ref", "slot": "ref", "values": vals([ss] * len(weeks))},
            ],
        }]
    else:
        pab_row = []

    # ---- RCCP ------------------------------------------------------------
    if res.rccp is not None:
        for rid, grp in res.rccp.groupby("resource"):
            before = res.rccp_before[res.rccp_before["resource"] == rid]
            weeks = list(grp["period"])
            pab_row.append({
                "title": f"Rough-cut capacity: {cfg.resources[rid].name}", "sub": "hours loaded per week by planned batch starts",
                "x": weeks, "xShort": [week_short(w) for w in weeks], "xName": "Week", "unit": "h",
                "series": [
                    {"name": "Before leveling", "kind": "bar", "slot": 2, "values": vals(before["load_h"])},
                    {"name": "After leveling", "kind": "bar", "slot": 1, "values": vals(grp["load_h"])},
                    {"name": "Capacity", "kind": "ref", "slot": "ref", "values": vals(grp["capacity_h"])},
                ],
            })
            tiles.append({
                "label": f"Peak load, {cfg.resources[rid].name}",
                "value": f"{grp['utilization'].max():.0%}",
                "status": ["good", "within capacity"] if not grp["overloaded"].any() else ["bad", "overloaded"],
                "note": f"{before['utilization'].max():.0%} before leveling · {len(res.rccp_moves)} batch move(s)",
            })
    if pab_row:
        rows.append(pab_row)

    # ---- purchasing ------------------------------------------------------
    purch_row = []
    priced = [i for i in (res.spend.index if res.spend is not None else []) if not str(i).startswith("TOTAL")]
    if priced:
        item = priced[0]
        mt = res.mrp[item].table
        weeks = list(mt.columns)
        purch_row.append({
            "title": f"Purchasing: {item} receipts and on-hand", "sub": f"kg · planned PO receipts from MRP ({cfg.items[item].planning.lot_sizing.rule.replace('_', ' ')})",
            "x": weeks, "xShort": [week_short(w) for w in weeks], "xName": "Week", "unit": "kg",
            "series": [
                {"name": "PO receipts (planned + open)", "kind": "bar", "slot": 1, "values": vals(mt.loc["planned_order_receipts"] + mt.loc["scheduled_receipts"])},
                {"name": "Projected on hand", "kind": "line", "slot": 3, "values": vals(mt.loc["projected_on_hand"])},
                {"name": "Safety stock", "kind": "ref", "slot": "ref", "values": vals([cfg.items[item].planning.safety_stock] * len(weeks))},
            ],
        })
        sp = res.spend.loc["TOTAL (priced items)"]
        sc = res.price_scenarios
        purch_row.append({
            "title": "Feedstock spend over the horizon, by price scenario", "sub": f"USD for {', '.join(priced)} · p10/p50/p90 of monthly prices since {sc['window_start'].min()} · corn content only",
            "x": ["p10 (low)", "p50 (median)", f"latest ({sc['base_date'].max()})", "p90 (high)"], "xName": "Scenario", "unit": "USD",
            "series": [{"name": "Spend", "kind": "bar", "slot": 1, "values": vals([sp["low_p10"], sp["median_p50"], sp["base"], sp["high_p90"]])}],
            "source": IMF,
        })
        tiles.append({
            "label": f"Feedstock spend, {cfg.horizon} weeks",
            "value": money(sp["base"]),
            "note": f"p10–p90 {money(sp['low_p10'])}–{money(sp['high_p90'])}; not priced: {len(res.spend_excluded)} items",
        })
    if purch_row:
        rows.append(purch_row)

    # ---- sourcing (M6) ----------------------------------------------------
    if res.awards is not None and len(res.awards):
        aw, q, tc = res.awards, res.quotes, res.tco
        item = priced[0] if priced else str(aw.index[0])
        uom = cfg.items[item].uom
        bids = q[q["item"] == item].sort_values("rank")
        names = [short_name(n) for n in bids["supplier_name"]]
        w = cfg.sourcing.weights
        winners = aw["awarded_name"].nunique()
        tiles.append({
            "label": f"RFQ awards ({len(aw)} items, {len(cfg.suppliers)} suppliers)",
            "value": f"{winners} different winner{'s' if winners > 1 else ''}",
            "note": f"weights: price {w['price']:.0%}, quality {w['quality']:.0%}, "
                    f"lead time {w['lead_time']:.0%}, risk {w['risk']:.0%} · quotes are MOCK",
        })
        tiles.append({
            "label": "Items where the lowest price is not the lowest total cost",
            "value": f"{len(res.tco_notes)} / {len(aw)}",
            "status": ["bad", "price alone would mis-award"] if res.tco_notes else ["good", "price and TCO agree"],
            "note": "freight and duty by incoterm, MOQ carrying cost, cost of defects",
        })
        rows.append([
            {"title": f"RFQ scorecard: {item}", "sub": "weighted score by criterion, stacked to the total · "
                      "each criterion range-normalised inside the bid set (best 1, worst 0) · quotes are MOCK",
             "x": names, "xName": "Bidder", "unit": "score", "digits": 3, "stacked": True,
             "series": [
                 {"name": f"Price ({w['price']:.0%})", "kind": "bar", "slot": 1, "values": vals(bids["price_score"] * w["price"])},
                 {"name": f"Quality ({w['quality']:.0%})", "kind": "bar", "slot": 2, "values": vals(bids["quality_score"] * w["quality"])},
                 {"name": f"Lead time ({w['lead_time']:.0%})", "kind": "bar", "slot": 3, "values": vals(bids["lead_time_score"] * w["lead_time"])},
                 {"name": f"Risk ({w['risk']:.0%})", "kind": "bar", "slot": 4, "values": vals(bids["risk_score_norm"] * w["risk"])},
             ]},
            {"title": f"Should-cost vs quotes: {item}", "sub": f"USD per {uom} · target = material "
                      f"({res.should_cost.loc[item, 'material_basis']}) + conversion + margin [mock shares]",
             "x": names, "xName": "Bidder", "unit": f"USD/{uom}", "digits": 3,
             "series": [
                 {"name": "Quoted price", "kind": "bar", "slot": 1, "values": vals(bids["quoted_usd_per_uom"])},
                 {"name": "Should-cost target", "kind": "ref", "slot": "ref", "values": vals([res.should_cost.loc[item, "target_price_usd"]] * len(bids))},
             ]},
        ])
        t_item = tc[tc["item"] == item].set_index("supplier").reindex(bids["supplier"])
        sc_rows = []
        if res.scorecard is not None and len(res.scorecard):
            sc = res.scorecard.reset_index()
            sc_rows.append({
                "title": "Supplier scorecard: delivered vs quoted OTIF",
                "sub": f"{cfg.sourcing.scorecard_periods} simulated delivery periods per awarded supplier · MOCK performance",
                "x": list(sc["item"]), "xName": "Item", "unit": "share", "digits": 3,
                "series": [
                    {"name": "OTIF delivered", "kind": "bar", "slot": 1, "values": vals(sc["otif_pct"])},
                    {"name": "On time", "kind": "bar", "slot": 3, "values": vals(sc["on_time_pct"])},
                    {"name": "Quoted OTIF", "kind": "ref", "slot": "ref", "values": vals(sc["quoted_otif_pct"])},
                ],
            })
        rows.append([
            {"title": f"Total cost of ownership: {item}", "sub": f"USD per {uom}, stacked · "
                      "quote plus what the quote does not say: freight and duty by incoterm, "
                      "carrying cost of the MOQ, cost of defects",
             "x": [f"{n} ({i})" for n, i in zip(names, t_item["incoterm"])], "xName": "Bidder", "unit": f"USD/{uom}",
             "digits": 3, "stacked": True,
             "series": [
                 {"name": "Unit price", "kind": "bar", "slot": 1, "values": vals(t_item["unit_price_usd"])},
                 {"name": "Freight", "kind": "bar", "slot": 2, "values": vals(t_item["freight_usd"])},
                 {"name": "Duty", "kind": "bar", "slot": 3, "values": vals(t_item["duty_usd"])},
                 {"name": "MOQ carrying", "kind": "bar", "slot": 4, "values": vals(t_item["moq_carrying_usd"])},
                 {"name": "Defect cost", "kind": "bar", "slot": 5, "values": vals(t_item["quality_cost_usd"])},
             ]},
        ] + sc_rows)
        if res.forward_buy is not None and len(res.forward_buy):
            fb = res.forward_buy[res.forward_buy["item"] == item]
            if len(fb):
                rows.append([{
                    "title": f"Forward buy vs spot: {item}",
                    "sub": f"USD per {uom} over {int(fb['weeks_covered'].iloc[0])} weeks of cover · forward = "
                           "today's quote plus carrying cost · spot passes each price scenario through at the "
                           "material share of the build-up",
                    "x": [r.replace("_", " ") for r in fb["scenario"]], "xName": "Price scenario",
                    "unit": f"USD/{uom}", "digits": 3,
                    "series": [
                        {"name": "Spot", "kind": "bar", "slot": 2, "values": vals(fb["spot_usd_per_uom"])},
                        {"name": "Forward buy (breakeven)", "kind": "ref", "slot": "ref", "values": vals(fb["forward_usd_per_uom"])},
                    ],
                    "source": IMF,
                }])

    # ---- feedstock cost history -------------------------------------------
    if res.feedstock_cost is not None:
        hist = pd.DataFrame({"base": res.feedstock_cost["total"]})
        for name, vr in variants.items():
            if vr.feedstock_cost is not None:
                hist[name] = vr.feedstock_cost["total"]
        hist = hist.dropna()
        labels = [d.strftime("%Y-%m") for d in hist.index]
        base_item = [b.component for b in cfg.bom if cfg.items[b.component].price is not None]
        series = [{"name": f"{base_item[0] if base_item else 'base'} (corn content)", "kind": "line", "slot": 1, "values": vals(hist["base"])}]
        for j, name in enumerate([c for c in hist.columns if c != "base"]):
            series.append({"name": f"{name} variant", "kind": "line", "slot": 2 + j, "values": vals(hist[name])})
        rows.append([{
            "title": f"Feedstock cost per kg of {root}, monthly since {labels[0][:4]}",
            "sub": "USD/kg · sugar needed per kg powder (cited process ratios) × commodity price · feedstock only",
            "x": labels, "xShort": [l[:4] for l in labels], "xName": "Month", "unit": "USD/kg", "digits": 3,
            "series": series, "height": 260, "source": IMF,
        }])
        tiles.append({
            "label": f"Feedstock cost per kg {root} ({labels[-1]})",
            "value": f"${hist['base'].iloc[-1]:.2f}",
            "note": " · ".join(f"{c}: ${hist[c].iloc[-1]:.2f}" for c in hist.columns if c != "base") or "latest month",
        })

    data = {
        "title": cfg.name,
        "subtitle": f"Planning report · S&OP → MPS → MRP → RCCP → purchasing → sourcing · generated {dt.date.today().isoformat()}",
        "banner": [
            ["Demand is MOCK.", "Inventory, lot sizes, reactor count and order book are mock planning assumptions."],
            ["Process parameters are cited", "(Behm et al. 2022, Humbird et al. 2011, EPA AP-42, USDA DME1)."],
            ["Prices:", "IMF via FRED. Spend and cost are feedstock-only."],
            ["Suppliers, quotes and supplier performance are MOCK", "and fictional; commodity prices are cited."],
        ],
        "tiles": tiles,
        "rows": rows,
        "footer": f"Config: {args.config} · every number traces to knowledge/assumptions.csv (cited or mock). {IMF}",
    }
    html = TEMPLATE.read_text().replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)
    print(f"wrote {args.out} ({len(html) / 1024:,.0f} KB, {sum(len(r) for r in rows)} charts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
