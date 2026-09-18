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
    ap = argparse.ArgumentParser(prog="ppsim", description="Production planning simulator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run demand -> BOM -> MRP for a product config")
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
