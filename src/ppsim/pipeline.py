"""Milestone-1 pipeline: config -> mock demand -> BOM -> MRP (+ FRED feedstock prices).

Returns DataFrames and optionally writes them as CSVs for downstream (static) reports.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from . import bom as bom_mod
from . import demand as demand_mod
from . import fred
from .config import ProductConfig, apply_variant, load_config
from .feedstock import item_prices, material_cost_per_unit
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
    fred_meta: List[dict] = field(default_factory=list)
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

    index = demand_mod.periods(cfg.start, cfg.horizon, cfg.freq)
    labels = list(index.astype(str))
    dem = demand_mod.generate(cfg.demand, index)

    root = cfg.demand.item
    planned = bom_mod.reachable(root, cfg.bom)
    bom_lines = [b for b in cfg.bom if b.parent in planned]
    explosion = bom_mod.explode(root, bom_lines)

    records = run_mrp(
        {i: cfg.items[i].planning for i in planned},
        bom_lines,
        {root: dem["qty"].to_numpy()},
        labels,
    )
    warnings = [w for r in records.values() for w in r.warnings]

    result = RunResult(cfg, dem, explosion, records, parameters_table(cfg), warnings=warnings)

    if fetch_prices:
        wanted = sorted({it.price.series for it in cfg.items.values() if it.price is not None})
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
    return result


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
        "horizon": {"start": cfg.start, "freq": cfg.freq, "buckets": cfg.horizon},
        "assumption_status_counts": result.parameters["status"].value_counts().to_dict(),
        "sources": sorted({(a.source, a.url) for a in cfg.assumptions.values() if a.status == "cited"}),
        "price_series": result.fred_meta,
        "warnings": result.warnings,
        "files": [p.name for p in written],
    }
    p = out / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2))
    written.append(p)
    return written
