"""Sales & operations planning (S&OP): monthly aggregate production plan.

Weekly demand is aggregated to calendar months (weeks that straddle a month boundary
are split by days). The plan meets a target ending inventory, expressed as months of
cover of the *next* month's demand, with either

- ``chase``: produce each month what that month needs to reach its target, or
- ``level``: one constant rate across the horizon that reaches the final target,

then caps production at capacity and flags shortfalls.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

STRATEGIES = ("chase", "level")
DAYS_PER_MONTH = 365.25 / 12  # calendar average, for "months of cover"


def week_month_weights(weeks: pd.PeriodIndex) -> pd.DataFrame:
    """Fraction of each week's days falling in each calendar month (rows sum to 1)."""
    months = pd.period_range(weeks[0].start_time, weeks[-1].end_time, freq="M")
    w = np.zeros((len(weeks), len(months)))
    for i, wk in enumerate(weeks):
        days = pd.date_range(wk.start_time.normalize(), wk.end_time.normalize(), freq="D")
        for d in days:
            w[i, months.get_loc(pd.Period(d, "M"))] += 1.0 / len(days)
    return pd.DataFrame(w, index=weeks, columns=months)


def days_per_month(weights: pd.DataFrame, days_per_week: float = 7.0) -> pd.Series:
    """Days of each month covered by the weekly horizon."""
    return pd.Series(weights.to_numpy().sum(axis=0) * days_per_week, index=weights.columns)


def aggregate(weekly: np.ndarray, weights: pd.DataFrame) -> pd.Series:
    """Weekly quantities -> monthly totals."""
    return pd.Series(weights.to_numpy().T @ np.asarray(weekly, dtype=float), index=weights.columns)


def disaggregate(monthly: pd.Series, weekly_profile: np.ndarray, weights: pd.DataFrame) -> np.ndarray:
    """Split monthly quantities into weeks in proportion to ``weekly_profile``.

    A week's share of month m is weight[w, m] * profile[w] / sum_w(weight * profile).
    Totals are conserved per month (for months with a positive profile).
    """
    W = weights.to_numpy()
    prof = np.asarray(weekly_profile, dtype=float)
    contrib = W * prof[:, None]  # weeks x months
    denom = contrib.sum(axis=0)
    share = np.divide(contrib, denom, out=np.zeros_like(contrib), where=denom > 0)
    return share @ monthly.reindex(weights.columns).fillna(0).to_numpy()


def plan(
    demand: pd.Series,
    opening_inventory: float,
    target_cover_months: float,
    strategy: str = "chase",
    capacity: Optional[pd.Series] = None,
    days: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Monthly S&OP production plan.

    ``demand``, ``capacity`` and ``days`` are indexed by month. ``days`` is the number of
    days of each month inside the planning horizon (edge months may be partial); it
    turns demand into a daily rate so the ending-inventory target of month m is
    ``target_cover_months`` x an average month of month m+1's rate (the last month uses
    its own rate).
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown S&OP strategy {strategy!r}; use one of {STRATEGIES}")
    d = demand.to_numpy(dtype=float)
    n = len(d)
    span = days.reindex(demand.index).to_numpy(dtype=float) if days is not None else np.full(n, DAYS_PER_MONTH)
    rate = np.divide(d, span, out=np.zeros(n), where=span > 0)
    nxt = np.append(rate[1:], rate[-1:]) if n else rate
    target = target_cover_months * nxt * DAYS_PER_MONTH
    cap = capacity.reindex(demand.index).to_numpy(dtype=float) if capacity is not None else np.full(n, np.inf)

    level_rate = max(0.0, (d.sum() + target[-1] - opening_inventory) / n) if n else 0.0

    prod = np.zeros(n)
    end = np.zeros(n)
    inv = opening_inventory
    for m in range(n):
        want = max(0.0, d[m] + target[m] - inv) if strategy == "chase" else level_rate
        prod[m] = min(want, cap[m])
        inv = inv + prod[m] - d[m]
        end[m] = inv

    util = np.divide(prod, cap, out=np.full(n, np.nan), where=np.isfinite(cap) & (cap > 0))
    out = pd.DataFrame(
        {
            "days": span,
            "demand": d,
            "production": prod,
            "ending_inventory": end,
            "target_inventory": target,
            "capacity": cap,
            "utilization": util,
        },
        index=demand.index.astype(str),
    )
    out.index.name = "month"
    out["capacity_limited"] = np.isfinite(cap) & (prod >= cap - 1e-9)
    out["stockout"] = end < -1e-9
    out["below_target"] = end < target - 1e-6
    return out
