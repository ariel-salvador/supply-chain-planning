"""Command line: ``python -m ppsim run <product.yaml> [--variant V] [--out DIR] [--offline]``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from . import fred
from .config import ConfigError
from .pipeline import run, write_outputs


def _fmt_mrp(table: pd.DataFrame, max_cols: int) -> str:
    t = table.iloc[:, :max_cols]
    return t.to_string(float_format=lambda v: f"{v:,.0f}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="ppsim", description="Supply chain planning engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run demand -> [S&OP -> MPS] -> MRP for a product config")
    r.add_argument("config", type=Path)
    r.add_argument("--variant", default=None, help="BOM variant defined in the config")
    r.add_argument("--out", type=Path, default=None, help="output directory (default outputs/<product>[-<variant>])")
    r.add_argument("--offline", action="store_true", help="use cached FRED data only")
    r.add_argument("--no-prices", action="store_true", help="skip FRED price series")
    r.add_argument("--cache-dir", type=Path, default=fred.DEFAULT_CACHE)
    r.add_argument("--show", type=int, default=8, help="MRP buckets to print (0 = none)")

    args = ap.parse_args(argv)
    try:
        res = run(args.config, variant=args.variant, fetch_prices=not args.no_prices, offline=args.offline, cache_dir=args.cache_dir)
    except (ConfigError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    out = args.out or Path("outputs") / (res.cfg.id + (f"-{res.cfg.variant}" if res.cfg.variant else ""))
    files = write_outputs(res, out)

    print(f"{res.cfg.name}  [variant: {res.cfg.variant or 'base'}]  (demand is MOCK)")
    print("\nBOM explosion per 1 unit of", res.cfg.demand.item)
    print(res.bom_explosion.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    if res.sop is not None:
        cols = ["days", "demand", "production", "ending_inventory", "target_inventory", "utilization"]
        print(f"\nS&OP ({res.cfg.sop.strategy}), monthly, demand is MOCK")
        print(res.sop[cols].to_string(float_format=lambda v: f"{v:,.2f}" if v < 10 else f"{v:,.0f}"))
    if res.mps is not None and args.show:
        print(f"\nMPS  {res.cfg.demand.item}  (DTF {res.mps.dtf}, PTF {res.mps.ptf}; first {args.show} buckets)")
        print(res.mps.to_frame().iloc[:, : args.show].to_string())
    if res.rccp is not None:
        print("\nRCCP (rough-cut capacity)")
        for rid, grp in res.rccp.groupby("resource"):
            b = res.rccp_before[res.rccp_before["resource"] == rid]
            print(f"  {rid}: capacity {grp['capacity_h'].iloc[0]:,.0f} h/bucket; peak utilization "
                  f"{b['utilization'].max():.0%} before leveling, {grp['utilization'].max():.0%} after; "
                  f"overloaded buckets {int(grp['overloaded'].sum())}")
        for m in res.rccp_moves:
            print("  leveled:", m)
    if res.po_lines is not None and len(res.po_lines):
        print(f"\nPurchasing: {res.po_lines['po'].nunique()} POs, {len(res.po_lines)} lines, "
              f"{res.po_lines['vendor'].nunique()} vendor(s)")
        if res.spend is not None and len(res.spend):
            t = res.spend.loc["TOTAL (priced items)"]
            print(f"  spend over horizon (priced items): base ${t['base']:,.0f}; "
                  f"p10-p90 ${t['low_p10']:,.0f}-${t['high_p90']:,.0f}")
        if res.spend_excluded:
            print("  not priced (no public price series):", ", ".join(res.spend_excluded))
    if res.awards is not None and len(res.awards):
        print(f"\nSourcing: {len(res.cfg.suppliers)} suppliers, {len(res.quotes)} quotes on {len(res.awards)} items "
              f"(quotes and supplier performance are MOCK)")
        w = res.cfg.sourcing.weights
        print("  RFQ weights: " + ", ".join(f"{k.replace('_', ' ')} {v:.0%}" for k, v in w.items()))
        aw = res.awards
        cols = ["bids", "awarded_name", "awarded_usd_per_uom", "awarded_score", "score_margin", "premium_vs_lowest_pct", "gap_vs_should_cost_pct"]
        print(aw[cols].to_string(float_format=lambda v: f"{v:,.3f}"))
        for item, row in aw.iterrows():
            print(f"  {item}: {row['rationale']}")
        for n in res.tco_notes:
            print("  TCO:", n)
        for n in res.sourcing_notes:
            print("  note:", n)
        if res.scorecard is not None and len(res.scorecard):
            print("\n  Supplier scorecard over "
                  f"{res.cfg.sourcing.scorecard_periods} simulated delivery periods (MOCK)")
            sc = res.scorecard[["supplier_name", "otif_pct", "on_time_pct", "in_full_pct", "fill_rate", "ppv_usd", "ppv_pct", "grade"]]
            print(sc.to_string(float_format=lambda v: f"{v:,.3f}"))
        for n in res.strategy_notes:
            print("  strategy:", n)
        if res.forward_buy is not None and len(res.forward_buy):
            for item, grp in res.forward_buy.groupby("item"):
                be = grp["breakeven_usd_per_uom"].iloc[0]
                spots = ", ".join(f"{r['scenario']} ${r['spot_usd_per_uom']:,.3f}" for _, r in grp.iterrows())
                print(f"  forward buy {item}: {int(grp['weeks_covered'].iloc[0])} weeks of cover breaks even at "
                      f"${be:,.3f}/{grp['uom'].iloc[0]}; scenario prices {spots}")
    if args.show:
        for item, rec in res.mrp.items():
            print(f"\nMRP  {item}  (lead time {rec.lead_time} buckets, first {args.show} buckets)")
            print(_fmt_mrp(rec.table, args.show))
    if res.feedstock_cost is not None and len(res.feedstock_cost):
        last = res.feedstock_cost.dropna().iloc[-1]
        print(f"\nFeedstock-only cost per unit, {res.feedstock_cost.dropna().index[-1]:%Y-%m}: "
              + ", ".join(f"{k} ${v:,.3f}" for k, v in last.items()))
    for w in res.warnings:
        print("warning:", w)
    print(f"\nwrote {len(files)} files to {out}/")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
