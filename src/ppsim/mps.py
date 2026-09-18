"""Master production schedule (MPS): weekly finished-goods plan with time fences and ATP.

Inputs per week: forecast, booked customer orders, firm (already committed) receipts,
and a candidate plan (normally the S&OP plan disaggregated to weeks).

- **Demand time fence (DTF):** before it, projected demand = customer orders only;
  from it onward, projected demand = max(forecast, orders).
- **Planning time fence (PTF, >= DTF):** before it the system creates no new planned
  MPS; only firm receipts count. Planned quantity that falls inside the fence is
  re-placed after it (catch-up): up to weekly capacity if known, otherwise evenly over
  the same number of weeks, so the S&OP volume isn't lost or lumped into one week.
- **Zones:** frozen (before DTF), slushy (DTF to PTF), liquid (after PTF).
- **Projected available balance (PAB):** on hand + firm + planned MPS - projected demand.
- **Available-to-promise (ATP):** discrete ATP with look-ahead: at each receipt week,
  receipt minus orders until the next receipt; shortfalls are covered by earlier ATP.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

ROWS = [
    "forecast",
    "customer_orders",
    "projected_demand",
    "firm_mps",
    "planned_mps",
    "projected_available_balance",
    "atp",
]


def projected_demand(forecast: np.ndarray, orders: np.ndarray, dtf: int) -> np.ndarray:
    f, o = np.asarray(forecast, dtype=float), np.asarray(orders, dtype=float)
    out = np.maximum(f, o)
    out[:dtf] = o[:dtf]
    return out


def apply_planning_fence(
    plan: np.ndarray,
    ptf: int,
    capacity: Optional[float] = None,
    firm: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Zero the weeks inside the fence and re-place their volume after it.

    Without ``capacity`` the volume is spread evenly over the next ``ptf`` weeks. With
    it, the volume fills the weeks after the fence up to capacity (net of firm
    receipts), earliest first. Anything that still doesn't fit goes to the first week
    after the fence, where the pipeline's capacity check flags it.
    """
    p = np.asarray(plan, dtype=float).copy()
    if ptf <= 0 or len(p) == 0:
        return p
    ptf = min(ptf, len(p))
    frozen = p[:ptf].sum()
    p[:ptf] = 0.0
    if ptf >= len(p) or frozen <= 0:
        return p
    if capacity is None:
        n = min(ptf, len(p) - ptf)
        p[ptf : ptf + n] += frozen / n
        return p
    f = np.zeros(len(p)) if firm is None else np.asarray(firm, dtype=float)
    remaining = frozen
    for t in range(ptf, len(p)):
        add = min(max(0.0, capacity - p[t] - f[t]), remaining)
        p[t] += add
        remaining -= add
        if remaining <= 1e-9:
            break
    if remaining > 1e-9:
        p[ptf] += remaining
    return p


def atp(on_hand: float, mps_total: np.ndarray, orders: np.ndarray) -> np.ndarray:
    """Discrete available-to-promise with look-ahead (backward netting of shortfalls)."""
    mps_total = np.asarray(mps_total, dtype=float)
    orders = np.asarray(orders, dtype=float)
    h = len(mps_total)
    receipts = [0] + [t for t in range(1, h) if mps_total[t] > 0]
    out = np.zeros(h)
    for i, k in enumerate(receipts):
        nxt = receipts[i + 1] if i + 1 < len(receipts) else h
        out[k] = (on_hand if k == 0 else 0.0) + mps_total[k] - orders[k:nxt].sum()
    # look-ahead: borrow shortfalls from earlier receipt weeks
    for i in range(len(receipts) - 1, 0, -1):
        k = receipts[i]
        if out[k] < 0:
            out[receipts[i - 1]] += out[k]
            out[k] = 0.0
    return out


@dataclass
class MpsResult:
    table: pd.DataFrame  # index = ROWS, columns = week labels (numeric)
    zones: List[str]  # frozen / slushy / liquid per week
    dtf: int
    ptf: int

    @property
    def planned(self) -> np.ndarray:
        return self.table.loc["planned_mps"].to_numpy()

    def to_frame(self) -> pd.DataFrame:
        """Table with a zone row, for display/CSV."""
        t = self.table.round(3).astype(object)
        t.loc["zone"] = self.zones
        return t


def build(
    forecast: Sequence[float],
    orders: Sequence[float],
    candidate_plan: Sequence[float],
    firm: Sequence[float],
    on_hand: float,
    dtf: int,
    ptf: int,
    labels: Sequence,
    capacity: Optional[float] = None,
) -> MpsResult:
    """Build the MPS for one finished item."""
    if dtf < 0 or ptf < dtf:
        raise ValueError(f"time fences must satisfy 0 <= DTF <= PTF (got DTF={dtf}, PTF={ptf})")
    f = np.asarray(forecast, dtype=float)
    o = np.asarray(orders, dtype=float)
    firm = np.asarray(firm, dtype=float)
    demand = projected_demand(f, o, dtf)
    planned = apply_planning_fence(candidate_plan, ptf, capacity, firm)
    pab = on_hand + np.cumsum(firm + planned - demand)
    table = pd.DataFrame(
        [f, o, demand, firm, planned, pab, atp(on_hand, firm + planned, o)],
        index=ROWS,
        columns=list(labels),
    )
    zones = ["frozen" if t < dtf else ("slushy" if t < ptf else "liquid") for t in range(len(f))]
    return MpsResult(table, zones, dtf, ptf)


def mock_orders(forecast: Sequence[float], booked_first: float, decay: float, seed: int = 0) -> np.ndarray:
    """MOCK booked customer orders: a share of forecast that decays with lead time.

    Week t is booked at ``booked_first * decay**t`` of forecast (+/- small noise),
    capped at 100 %.
    """
    f = np.asarray(forecast, dtype=float)
    t = np.arange(len(f))
    rng = np.random.default_rng(seed + 1)  # distinct stream from the demand noise
    share = np.clip(booked_first * decay ** t * (1 + 0.05 * rng.standard_normal(len(f))), 0, 1)
    return f * share
