"""Map external price series (e.g. FRED) onto purchased items and roll them up the BOM."""
from __future__ import annotations

from typing import Dict, Mapping

import pandas as pd

from .bom import total_requirements
from .config import ProductConfig, evaluate


def item_prices(cfg: ProductConfig, series: Mapping[str, pd.Series]) -> pd.DataFrame:
    """USD per item uom over time, for every item with a ``price`` link.

    Columns are item ids; the index is the union of the linked series' dates.
    """
    names = cfg.names()
    cols: Dict[str, pd.Series] = {}
    for item in cfg.items.values():
        if item.price is None:
            continue
        s = series[item.price.series]
        cols[item.id] = s.apply(lambda v, _i=item: evaluate(_i.price.usd_per_uom, {**names, _i.price.series: v}))
    return pd.DataFrame(cols).sort_index()


def material_cost_per_unit(cfg: ProductConfig, prices: pd.DataFrame, root: str) -> pd.DataFrame:
    """Priced-material cost to make one unit of ``root``, per date, by component.

    Only components with a price link are included; the total is therefore a partial
    (feedstock-only) cost, not a cost of goods.
    """
    req = total_requirements(root, cfg.bom)
    used = [c for c in req if c in prices.columns]
    out = pd.DataFrame({c: prices[c] * req[c] for c in used}, index=prices.index)
    out["total"] = out.sum(axis=1, min_count=1) if used else float("nan")
    return out.dropna(how="all")
