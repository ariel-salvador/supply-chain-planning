"""Purchasing: turn MRP planned releases of purchased items into a PO schedule and spend.

- One purchase order per vendor per release bucket; each purchased item's planned
  release becomes a line, due in its receipt bucket (release + lead time).
- Spend uses external price series (e.g. FRED) converted to USD per item uom:
  ``base`` = the latest observation; scenarios = low/median/high percentiles of the
  monthly prices over a trailing window. Items without a price link are listed as
  excluded. No price is invented for them.
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .config import ProductConfig
from .mrp import MrpRecord

# Scenario percentiles: a statistical convention for low / typical / high prices.
SCENARIOS: Tuple[Tuple[str, float], ...] = (("low_p10", 10.0), ("median_p50", 50.0), ("high_p90", 90.0))


def po_schedule(cfg: ProductConfig, records: Mapping[str, MrpRecord]) -> pd.DataFrame:
    """PO lines: po, vendor, item, qty, uom, order_bucket, order_period, due_bucket, due_period."""
    vendor_of = {i: v for v in cfg.vendors.values() for i in v.supplies}
    rows = []
    for iid, rec in records.items():
        item = cfg.items[iid]
        if item.type != "purchased":
            continue
        rel = rec.table.loc["planned_order_releases"].to_numpy()
        labels = list(rec.table.columns)
        vendor = vendor_of.get(iid)
        for t, q in enumerate(rel):
            if q <= 1e-9:
                continue
            due = t + rec.lead_time
            rows.append({
                "vendor": vendor.name if vendor else "(no vendor)",
                "vendor_id": vendor.id if vendor else "",
                "item": iid,
                "qty": q,
                "uom": item.uom,
                "order_bucket": t,
                "order_period": labels[t],
                "due_bucket": due,
                "due_period": labels[due] if due < len(labels) else "beyond horizon",
            })
    df = pd.DataFrame(rows, columns=["vendor", "vendor_id", "item", "qty", "uom", "order_bucket", "order_period", "due_bucket", "due_period"])
    if len(df):
        keys = df[["vendor_id", "order_bucket"]].drop_duplicates().reset_index(drop=True)
        keys["po"] = [f"PO-{k.vendor_id or 'NA'}-{k.order_bucket:02d}" for k in keys.itertuples()]
        df = df.merge(keys, on=["vendor_id", "order_bucket"]).sort_values(["order_bucket", "vendor", "item"])
        df = df[["po"] + [c for c in df.columns if c != "po"]].reset_index(drop=True)
    return df


def price_scenarios(prices: pd.DataFrame, window_years: float) -> pd.DataFrame:
    """USD per uom per item: base (latest) and percentile scenarios over the window."""
    rows = []
    for item in prices.columns:
        s = prices[item].dropna()
        if s.empty:
            continue
        recent = s[s.index > s.index.max() - pd.DateOffset(months=int(round(window_years * 12)))]
        row = {"item": item, "base": s.iloc[-1], "base_date": s.index[-1].strftime("%Y-%m"), "window_start": recent.index.min().strftime("%Y-%m")}
        for name, p in SCENARIOS:
            row[name] = float(np.percentile(recent, p))
        rows.append(row)
    return pd.DataFrame(rows).set_index("item") if rows else pd.DataFrame()


def spend(schedule: pd.DataFrame, scenarios: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, list]:
    """Spend by PO line (base price) and total spend by item for every scenario.

    Returns (lines_with_amount, totals_by_item_and_scenario, excluded_items).
    """
    lines = schedule.copy()
    priced = set(scenarios.index) if len(scenarios) else set()
    lines["usd_per_uom"] = lines["item"].map(scenarios["base"]) if priced else np.nan
    lines["amount_usd"] = lines["qty"] * lines["usd_per_uom"]
    excluded = sorted(set(lines["item"]) - priced)
    cols = ["base"] + [n for n, _ in SCENARIOS]
    totals = []
    for item, qty in lines.groupby("item")["qty"].sum().items():
        if item not in priced:
            continue
        totals.append({"item": item, "qty": qty, **{c: qty * scenarios.loc[item, c] for c in cols}})
    tot = pd.DataFrame(totals).set_index("item") if totals else pd.DataFrame(columns=["qty"] + cols)
    if len(tot):
        tot.loc["TOTAL (priced items)"] = [np.nan] + [tot[c].sum() for c in cols]
    return lines, tot, excluded
