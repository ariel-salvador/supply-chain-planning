"""Time-phased MRP (material requirements planning).

Classic record per item and bucket:

    gross requirements        independent demand + parents' planned releases x qty_per
    scheduled receipts        open orders already released
    projected on hand         end-of-bucket inventory after planned receipts
    net requirements          shortfall vs. safety stock before planned receipts
    planned order receipts    lot-sized net requirements
    planned order releases    planned receipts offset by the item's lead time

Items are processed in low-level-code order so each item's gross requirements are
complete before netting. Buckets are integer indices 0..horizon-1; labels are cosmetic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence

import numpy as np
import pandas as pd

from .bom import children, low_level_codes
from .config import BomLine, LotSizing, Planning

ROWS = [
    "gross_requirements",
    "scheduled_receipts",
    "projected_on_hand",
    "net_requirements",
    "planned_order_receipts",
    "planned_order_releases",
]

_EPS = 1e-9


def lot_size(net: float, lot: LotSizing, future_net: Sequence[float] = ()) -> float:
    """Planned receipt quantity to cover ``net`` in the current bucket.

    ``future_net`` is the uncovered requirement in the following buckets (used by
    periods-of-supply). Minimum and multiple constraints are applied last.
    """
    if net <= _EPS:
        return 0.0
    if lot.rule == "lot_for_lot":
        q = net
    elif lot.rule == "fixed_order_quantity":
        q = lot.quantity * math.ceil(net / lot.quantity - _EPS)
    elif lot.rule == "periods_of_supply":
        q = net + sum(max(x, 0.0) for x in list(future_net)[: lot.periods - 1])
    else:  # pragma: no cover - validated in config
        raise ValueError(lot.rule)
    q = max(q, lot.minimum)
    if lot.multiple > 0:
        q = lot.multiple * math.ceil(q / lot.multiple - _EPS)
    return q


@dataclass
class MrpRecord:
    item: str
    lead_time: int
    table: pd.DataFrame  # index = ROWS, columns = period labels
    past_due_release: float = 0.0  # releases that would fall before bucket 0
    warnings: List[str] = field(default_factory=list)


def mrp_item(
    item: str,
    gross: np.ndarray,
    planning: Planning,
    labels: Sequence,
) -> MrpRecord:
    """Net, lot-size and offset one item."""
    h = len(gross)
    sched = np.zeros(h)
    warnings: List[str] = []
    for t, q in planning.scheduled_receipts.items():
        if 0 <= t < h:
            sched[t] += q
        else:
            warnings.append(f"{item}: scheduled receipt in bucket {t} is outside the horizon; ignored")

    poh = np.zeros(h)
    net = np.zeros(h)
    por = np.zeros(h)
    ss = planning.safety_stock
    prev = planning.on_hand
    if prev < ss:
        warnings.append(f"{item}: starting on-hand {prev:g} is below safety stock {ss:g}")

    for t in range(h):
        available = prev + sched[t] - gross[t]
        if available < ss - _EPS:
            net[t] = ss - available
            # later buckets' requirement net of open orders (for periods of supply)
            future = gross[t + 1 :] - sched[t + 1 :]
            por[t] = lot_size(net[t], planning.lot_sizing, future)
        poh[t] = available + por[t]
        prev = poh[t]

    lt = planning.lead_time
    rel = np.zeros(h)
    past_due = 0.0
    for t in range(h):
        if por[t] <= 0:
            continue
        if t - lt >= 0:
            rel[t - lt] += por[t]
        else:
            past_due += por[t]
    if past_due > _EPS:
        warnings.append(
            f"{item}: {past_due:,.0f} of planned releases fall before the horizon start "
            f"(lead time {lt}); expedite or add scheduled receipts"
        )

    table = pd.DataFrame(
        [gross, sched, poh, net, por, rel], index=ROWS, columns=list(labels)
    )
    return MrpRecord(item, lt, table, past_due, warnings)


def run_mrp(
    items: Mapping[str, Planning],
    bom: Sequence[BomLine],
    independent_demand: Mapping[str, Sequence[float]],
    labels: Sequence,
) -> Dict[str, MrpRecord]:
    """Run MRP for every item in ``items`` over ``len(labels)`` buckets."""
    h = len(labels)
    for i, d in independent_demand.items():
        if i not in items:
            raise KeyError(f"independent demand for unknown item {i!r}")
        if len(d) != h:
            raise ValueError(f"demand for {i!r} has {len(d)} buckets, expected {h}")
    for b in bom:
        if b.parent not in items or b.component not in items:
            raise KeyError(f"BOM line {b.parent}->{b.component} references an item not being planned")

    llc = low_level_codes(list(items), bom)
    kids = children(bom)
    gross: Dict[str, np.ndarray] = {i: np.zeros(h) for i in items}
    for i, d in independent_demand.items():
        gross[i] += np.asarray(d, dtype=float)

    out: Dict[str, MrpRecord] = {}
    for item in sorted(items, key=lambda i: (llc[i], i)):
        rec = mrp_item(item, gross[item], items[item], labels)
        out[item] = rec
        releases = rec.table.loc["planned_order_releases"].to_numpy().copy()
        # past-due releases still consume components: charge them to the first bucket
        releases[0] += rec.past_due_release
        for line in kids.get(item, []):
            gross[line.component] += releases * line.qty_per
    return out


def to_long(records: Mapping[str, MrpRecord]) -> pd.DataFrame:
    """Stack MRP tables into long format: item, period, row, qty."""
    frames = []
    for item, rec in records.items():
        df = rec.table.copy()
        df.index.name = "row"
        long = df.reset_index().melt(id_vars="row", var_name="period", value_name="qty")
        long.insert(0, "item", item)
        frames.append(long)
    if not frames:
        return pd.DataFrame(columns=["item", "period", "row", "qty"])
    return pd.concat(frames, ignore_index=True)
