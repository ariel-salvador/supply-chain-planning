"""Pipeline: config -> mock demand -> [S&OP -> MPS] -> MRP (+ FRED feedstock prices).

Without ``sop``/``mps`` in the config, MRP nets the weekly mock demand directly (M1).
With them (M2), demand is aggregated to a monthly S&OP plan, disaggregated into a
weekly MPS with time fences and ATP, and the MPS drives MRP for the finished item.

Returns DataFrames and optionally writes them as CSVs for downstream (static) reports.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from . import bom as bom_mod
from . import mps as mps_mod
from . import purchasing as purch_mod
from . import rccp as rccp_mod
from . import sop as sop_mod
from . import sourcing as src_mod
from . import supplier_perf as perf_mod
from . import demand as demand_mod
from . import fred
from .config import ProductConfig, apply_variant, load_config
from .feedstock import indexed_prices, item_prices, material_cost_per_unit
from .mrp import MrpRecord, run_mrp, to_long


@dataclass
class RunResult:
    cfg: ProductConfig
    demand: pd.DataFrame
    bom_explosion: pd.DataFrame
    mrp: Dict[str, MrpRecord]
    parameters: pd.DataFrame
    prices: Optional[pd.DataFrame] = None
    feedstock_cost: Optional[pd.DataFrame] = None
    sop: Optional[pd.DataFrame] = None
    mps: Optional[mps_mod.MpsResult] = None
    rccp: Optional[pd.DataFrame] = None  # load after leveling (or as planned if no leveling)
    rccp_before: Optional[pd.DataFrame] = None  # load before leveling
    rccp_moves: List[str] = field(default_factory=list)
    po_lines: Optional[pd.DataFrame] = None
    price_scenarios: Optional[pd.DataFrame] = None
    spend: Optional[pd.DataFrame] = None
    spend_excluded: List[str] = field(default_factory=list)
    usage: Optional[pd.DataFrame] = None  # purchased volume the plan implies (M6)
    should_cost: Optional[pd.DataFrame] = None
    quotes: Optional[pd.DataFrame] = None  # supplier master + RFQ responses, scored
    awards: Optional[pd.DataFrame] = None
    tco: Optional[pd.DataFrame] = None
    tco_notes: List[str] = field(default_factory=list)
    delivery_history: Optional[pd.DataFrame] = None
    scorecard: Optional[pd.DataFrame] = None
    safety_stock: Optional[pd.DataFrame] = None
    strategy: Optional[pd.DataFrame] = None
    strategy_notes: List[str] = field(default_factory=list)
    forward_buy: Optional[pd.DataFrame] = None
    sourcing_notes: List[str] = field(default_factory=list)  # award vs planning parameters
    fred_meta: List[dict] = field(default_factory=list)
    index_prices: Optional[pd.DataFrame] = None  # mock bases moved by a cited index (should-cost, history)
    warnings: List[str] = field(default_factory=list)

    @property
    def mrp_long(self) -> pd.DataFrame:
        return to_long(self.mrp)


def parameters_table(cfg: ProductConfig) -> pd.DataFrame:
    """Every number the run used, with its registry label and citation."""
    rows = [
        {
            "id": a.id,
            "name": a.name,
            "value": a.value,
            "unit": a.unit,
            "status": a.status,
            "confidence": a.confidence,
            "source": a.source,
            "url": a.url,
            "retrieved": a.retrieved,
        }
        for a in cfg.assumptions.values()
    ]
    rows += [{"id": k, "name": "derived", "value": v, "status": "derived"} for k, v in cfg.derived.items()]
    return pd.DataFrame(rows)


def run(
    config: Union[str, Path, ProductConfig],
    variant: Optional[str] = None,
    fetch_prices: bool = True,
    offline: bool = False,
    cache_dir: Union[str, Path] = fred.DEFAULT_CACHE,
) -> RunResult:
    cfg = config if isinstance(config, ProductConfig) else load_config(config)
    cfg = apply_variant(cfg, variant)

    root = cfg.demand.item
    planned = bom_mod.reachable(root, cfg.bom)
    bom_lines = [b for b in cfg.bom if b.parent in planned]
    explosion = bom_mod.explode(root, bom_lines)
    plan_items = {i: cfg.items[i].planning for i in planned}

    if cfg.sop is None:
        index = demand_mod.periods(cfg.start, cfg.horizon, cfg.freq)
        labels = list(index.astype(str))
        dem = demand_mod.generate(cfg.demand, index)
        records = run_mrp(plan_items, bom_lines, {root: dem["qty"].to_numpy()}, labels)
        sop_df, mps_res, extra = None, None, []
    else:
        dem, labels, sop_df, mps_res, extra = _sop_mps(cfg, root)
        records = run_mrp(
            plan_items,
            bom_lines,
            {root: mps_res.table.loc["projected_demand"].to_numpy()},
            labels,
            fixed_receipts={root: mps_res.planned},
        )
    indep = {root: (mps_res.table.loc["projected_demand"].to_numpy() if mps_res is not None else dem["qty"].to_numpy())}
    fixed = {root: mps_res.planned} if mps_res is not None else {}
    rccp_before = rccp_after = None
    moves: List[str] = []
    if cfg.bill_of_resources:
        records, rccp_before, rccp_after, moves = _rccp(cfg, records, plan_items, bom_lines, indep, fixed, labels)
        over = rccp_after[rccp_after["overloaded"]]
        for rid, grp in over.groupby("resource"):
            extra.append(f"RCCP: {rid} overloaded in {len(grp)} bucket(s), first {grp['period'].iloc[0]}")
    warnings = extra + [w for r in records.values() for w in r.warnings]

    result = RunResult(
        cfg, dem, explosion, records, parameters_table(cfg), sop=sop_df, mps=mps_res,
        rccp=rccp_after, rccp_before=rccp_before, rccp_moves=moves, warnings=warnings,
    )

    if fetch_prices:
        wanted = sorted({it.price.series for it in cfg.items.values() if it.price is not None}
                        | set(cfg.sourcing.material_index.values() if cfg.sourcing else ()))
        series = {}
        for sid in wanted:
            try:
                series[sid] = fred.fetch_series(sid, cache_dir=cache_dir, offline=offline)
                result.fred_meta.append(fred.cache_metadata(sid, cache_dir))
            except fred.FredError as e:
                result.warnings.append(f"price series skipped: {e}")
        priced = {k: v for k, v in cfg.items.items() if v.price is not None and v.price.series in series}
        if priced:
            result.prices = item_prices(cfg, series)
            result.feedstock_cost = material_cost_per_unit(cfg, result.prices, root)
        idx = indexed_prices(cfg, series)
        if not idx.empty:
            result.index_prices = idx

    if cfg.purchasing and result.prices is not None:
        result.price_scenarios = purch_mod.price_scenarios(result.prices, cfg.purchasing.price_window_years)

    vendor_of = None
    if cfg.sourcing:
        _sourcing(cfg, result, records)
        if result.awards is not None:
            vendor_of = src_mod.awarded_vendor_map(result.awards, cfg)

    if cfg.vendors or cfg.purchasing or vendor_of:
        result.po_lines = purch_mod.po_schedule(cfg, records, vendor_of)
        if result.price_scenarios is not None:
            result.po_lines, result.spend, result.spend_excluded = purch_mod.spend(result.po_lines, result.price_scenarios)
        if cfg.sourcing and result.awards is not None:
            # does the plan actually reach the awarded supplier's minimum order quantity?
            result.po_lines, moq = src_mod.check_moq(result.po_lines, result.quotes, result.awards)
            result.sourcing_notes += moq
    return result


def _sourcing(cfg: ProductConfig, result: RunResult, records) -> None:
    """M6: should-cost -> RFQ scoring -> award -> TCO -> scorecard -> strategy."""
    latest = {}
    for frame in (result.prices, result.index_prices):
        if frame is None:
            continue
        for col in frame.columns:
            s = frame[col].dropna()
            if len(s):
                latest[col] = float(s.iloc[-1])
    result.usage = src_mod.planned_usage(cfg, records)
    result.should_cost = src_mod.should_cost(cfg, latest)
    quotes = src_mod.score_quotes(cfg, src_mod.quote_table(cfg, result.should_cost, result.usage))
    result.quotes = quotes
    result.awards = src_mod.award(cfg, quotes)
    result.tco = src_mod.tco(cfg, quotes, result.usage)
    result.tco_notes = src_mod.tco_notes(result.tco)
    result.delivery_history = perf_mod.delivery_history(cfg, quotes, result.awards, result.usage)
    result.scorecard = perf_mod.scorecard(cfg, result.delivery_history, quotes)
    result.safety_stock = perf_mod.safety_stock_cost(cfg, quotes, result.tco, result.usage, result.awards)
    result.strategy = perf_mod.source_strategy(cfg, quotes, result.awards, result.tco, result.usage)
    result.strategy_notes = perf_mod.strategy_notes(result.strategy)
    result.forward_buy = perf_mod.forward_buy(cfg, result.awards, result.should_cost, result.usage, result.price_scenarios)
    for iid, aw in result.awards.iterrows():
        planned_lt = cfg.items[iid].planning.lead_time
        if int(aw["awarded_lead_time_weeks"]) != planned_lt:
            result.sourcing_notes.append(
                f"sourcing: {iid} awarded to {aw['awarded_to']} at {int(aw['awarded_lead_time_weeks'])}-week lead time "
                f"vs {planned_lt} planned; update the planning parameter and re-plan"
            )
        if aw["bids"] < 2:
            result.sourcing_notes.append(f"sourcing: {iid} had only {aw['bids']} bid; no competitive comparison")


def _rccp(cfg: ProductConfig, records, plan_items, bom_lines, indep, fixed, labels):
    """Load resources from planned releases; optionally level and re-run MRP."""
    bor = [b for b in cfg.bill_of_resources if b.item in records]

    def releases(recs):
        return {i: recs[i].table.loc["planned_order_releases"].to_numpy() for i in recs}

    before = rccp_mod.load_profile(releases(records), bor, cfg.resources, labels)
    if not (cfg.rccp and cfg.rccp.level and before["overloaded"].any()):
        return records, before, before, []

    h = len(labels)
    new_fixed = dict(fixed)
    moves: List[str] = []
    rel_all = releases(records)
    for line in bor:
        res = cfg.resources[line.resource]
        other = np.zeros(h)
        for o in bor:
            if o.resource == line.resource and o.item != line.item and o.item in rel_all:
                other += rel_all[o.item] * o.hours_per_unit
        lot = cfg.items[line.item].planning.lot_sizing
        leveled, notes = rccp_mod.level(
            rel_all[line.item], line.hours_per_unit, res.capacity_h,
            lot.multiple or lot.quantity, cfg.rccp.max_pull_forward, other,
        )
        if np.allclose(leveled, rel_all[line.item]):
            continue
        rec = records[line.item]
        lt = rec.lead_time
        receipts = rec.table.loc["planned_order_receipts"].to_numpy().copy()
        receipts[lt:] = 0.0
        for t in range(h - lt):
            receipts[t + lt] += leveled[t]
        new_fixed[line.item] = receipts
        moves += [f"{line.item}: {n.replace('bucket', 'week')}" for n in notes]
        rel_all[line.item] = leveled
    if len(new_fixed) == len(fixed):
        return records, before, before, moves
    records = run_mrp(plan_items, bom_lines, indep, labels, fixed_receipts=new_fixed)
    after = rccp_mod.load_profile(releases(records), bor, cfg.resources, labels)
    return records, before, after, moves


def sop_weeks(start: str, months: int, freq: str) -> pd.PeriodIndex:
    """Weekly buckets from ``start`` whose end falls within ``months`` calendar months."""
    first = pd.Period(pd.Timestamp(start), "M")
    last_day = (first + months - 1).end_time
    weeks = pd.period_range(start=start, end=last_day, freq=freq)
    return weeks[weeks.end_time <= last_day]


def _sop_mps(cfg: ProductConfig, root: str):
    weeks = sop_weeks(cfg.start, cfg.sop_months, cfg.freq)
    if len(weeks) < cfg.horizon:
        raise ValueError(f"S&OP span ({len(weeks)} weeks) is shorter than the MPS/MRP horizon ({cfg.horizon})")
    dem = demand_mod.generate(cfg.demand, weeks)
    forecast = dem["qty"].to_numpy()

    weights = sop_mod.week_month_weights(weeks)
    days = sop_mod.days_per_month(weights)
    monthly = sop_mod.aggregate(forecast, weights)
    capacity = None
    if cfg.sop.capacity_per_week is not None:
        capacity = days / 7.0 * cfg.sop.capacity_per_week
    fg = cfg.items[root].planning
    horizon_firm = sum(q for t, q in fg.scheduled_receipts.items() if 0 <= t < cfg.horizon)
    sop_df = sop_mod.plan(
        monthly, fg.on_hand + horizon_firm, cfg.sop.target_cover_months, cfg.sop.strategy, capacity, days
    )

    h = cfg.horizon
    labels = list(weeks[:h].astype(str))
    candidate = sop_mod.disaggregate(sop_df["production"].set_axis(weights.columns), forecast, weights)[:h]
    d = cfg.demand
    orders = (
        mps_mod.mock_orders(forecast[:h], d.orders_booked_first, d.orders_decay, d.seed)
        if d.orders_booked_first is not None
        else np.zeros(h)
    )
    firm = np.zeros(h)
    for t, q in fg.scheduled_receipts.items():
        if 0 <= t < h:
            firm[t] += q
    mps_res = mps_mod.build(
        forecast[:h], orders, candidate, firm, fg.on_hand, cfg.mps.demand_time_fence, cfg.mps.planning_time_fence, labels,
        capacity=cfg.sop.capacity_per_week,
    )

    warnings = []
    for flag, what in (("stockout", "projected stockout"), ("capacity_limited", "production capped at capacity"), ("below_target", "ending inventory below target")):
        months = list(sop_df.index[sop_df[flag]])
        if months:
            warnings.append(f"S&OP: {what} in {', '.join(months)}")
    pab = mps_res.table.loc["projected_available_balance"]
    low = [str(c) for c, v in pab.items() if v < fg.safety_stock - 1e-6]
    if low:
        warnings.append(f"MPS {root}: projected available balance below safety stock in {len(low)} week(s), first {low[0]}")
    if cfg.sop.capacity_per_week is not None:
        load = mps_res.table.loc["firm_mps"] + mps_res.table.loc["planned_mps"]
        over = [str(c) for c, v in load.items() if v > cfg.sop.capacity_per_week + 1e-6]
        if over:
            warnings.append(f"MPS {root}: weekly schedule exceeds capacity in {len(over)} week(s), first {over[0]}")
    if mps_res.table.loc["atp"].iloc[0] < -1e-6:
        warnings.append(f"MPS {root}: customer orders exceed supply (negative ATP in first week)")
    return dem, labels, sop_df, mps_res, warnings


def write_outputs(result: RunResult, out_dir: Union[str, Path]) -> List[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    def save(df: pd.DataFrame, name: str, index: bool = False) -> None:
        p = out / name
        df.to_csv(p, index=index)
        written.append(p)

    save(result.demand, "demand_mock.csv")
    save(result.bom_explosion, "bom_explosion.csv")
    save(result.parameters, "parameters.csv")
    if result.sop is not None:
        save(result.sop, "sop_plan.csv", index=True)
    if result.mps is not None:
        save(result.mps.to_frame(), f"mps_{result.cfg.demand.item}.csv", index=True)
    if result.rccp is not None:
        save(result.rccp, "rccp_load.csv")
    if result.po_lines is not None:
        save(result.po_lines, "po_schedule.csv")
    if result.price_scenarios is not None and len(result.price_scenarios):
        save(result.price_scenarios, "price_scenarios_usd_per_uom.csv", index=True)
    if result.spend is not None:
        save(result.spend, "spend_by_scenario.csv", index=True)
    for df, name, idx in (
        (result.usage, "sourcing_planned_usage.csv", True),
        (result.should_cost, "sourcing_should_cost.csv", True),
        (result.quotes, "sourcing_quotes_scored.csv", False),
        (result.awards, "sourcing_awards.csv", True),
        (result.tco, "sourcing_tco.csv", False),
        (result.delivery_history, "supplier_delivery_history.csv", False),
        (result.scorecard, "supplier_scorecard.csv", True),
        (result.safety_stock, "sourcing_safety_stock_cost.csv", False),
        (result.strategy, "sourcing_strategy.csv", False),
        (result.forward_buy, "sourcing_forward_buy.csv", False),
    ):
        if df is not None and len(df):
            save(df, name, index=idx)
    save(result.mrp_long, "mrp_long.csv")
    for item, rec in result.mrp.items():
        save(rec.table.round(3), f"mrp_{item}.csv", index=True)
    if result.prices is not None:
        save(result.prices, "feedstock_prices_usd_per_uom.csv", index=True)
    if result.feedstock_cost is not None:
        save(result.feedstock_cost, "feedstock_cost_per_unit.csv", index=True)

    cfg = result.cfg
    manifest = {
        "product": cfg.id,
        "name": cfg.name,
        "config": str(cfg.path) if cfg.path else None,
        "variant": cfg.variant,
        "demand_is_mock": True,
        "planning_parameters_are_assumptions": True,
        "horizon": {"start": cfg.start, "freq": cfg.freq, "buckets": cfg.horizon, "sop_months": cfg.sop_months or None},
        "sop": None if cfg.sop is None else {"strategy": cfg.sop.strategy, "target_cover_months": cfg.sop.target_cover_months, "capacity_per_week": cfg.sop.capacity_per_week},
        "mps": None if cfg.mps is None else {"demand_time_fence": cfg.mps.demand_time_fence, "planning_time_fence": cfg.mps.planning_time_fence},
        "sourcing": None if cfg.sourcing is None else {
            "suppliers": len(cfg.suppliers),
            "items_quoted": 0 if result.quotes is None else int(result.quotes["item"].nunique()),
            "rfq_weights": cfg.sourcing.weights,
            "quotes_and_supplier_performance_are_mock": True,
            "awards": {} if result.awards is None else {i: r["awarded_to"] for i, r in result.awards.iterrows()},
            "notes": result.sourcing_notes,
            "tco_notes": result.tco_notes,
            "strategy_notes": result.strategy_notes,
        },
        "assumption_status_counts": result.parameters["status"].value_counts().to_dict(),
        "sources": sorted({(a.source, a.url) for a in cfg.assumptions.values() if a.status == "cited"}),
        "price_series": result.fred_meta,
        "spend_excludes_unpriced_items": result.spend_excluded,
        "warnings": result.warnings,
        "files": [p.name for p in written],
    }
    p = out / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2))
    written.append(p)
    return written
