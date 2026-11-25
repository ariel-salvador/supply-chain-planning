"""Seeded mock demand generator.

Demand is synthetic by design: trend x seasonality x noise around a base rate. Output
always carries ``mock=True`` so nothing downstream can mistake it for real data.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .config import DemandSpec


def periods(start: str, horizon: int, freq: str) -> pd.PeriodIndex:
    return pd.period_range(start=start, periods=horizon, freq=freq)


def generate(spec: DemandSpec, index: pd.PeriodIndex, anchor: Optional[pd.Timestamp] = None,
             seed: Optional[int] = None) -> pd.DataFrame:
    """Generate demand for ``spec.item`` over ``index``.

    - trend: compound ``annual_growth`` applied continuously from ``anchor`` (default:
      the first period). Anchoring a past index at the plan's start makes the history
      grow *into* the forward plan's base rate, so the plan itself doesn't change
    - ``seed`` overrides ``spec.seed``: history draws its noise from its own stream, so
      the forward plan's committed numbers stay exactly as they were
    - seasonality: cosine with amplitude ``seasonal_amplitude`` (fraction of base),
      peaking in ``seasonal_peak_month``
    - noise: multiplicative normal with coefficient of variation ``noise_cv``,
      reproducible via ``seed``; quantities are clipped at zero
    """
    start = index[0].start_time if anchor is None else pd.Timestamp(anchor)
    mid = index.start_time + (index.end_time - index.start_time) / 2
    years = np.asarray((mid - start).days, dtype=float) / 365.25  # negative before the anchor
    trend = (1.0 + spec.annual_growth) ** years

    # fractional month of year at each period's midpoint (1.0 = Jan 1)
    month_pos = np.asarray(mid.month, dtype=float) + (np.asarray(mid.day, dtype=float) - 1) / 30.4
    season = 1.0 + spec.seasonal_amplitude * np.cos(2 * np.pi * (month_pos - spec.seasonal_peak_month - 0.5) / 12)

    rng = np.random.default_rng(spec.seed if seed is None else seed)
    noise = 1.0 + spec.noise_cv * rng.standard_normal(len(index)) if spec.noise_cv > 0 else np.ones(len(index))

    qty = np.clip(spec.base_per_period * trend * season * noise, 0, None)
    return pd.DataFrame(
        {
            "period": index.astype(str),
            "item": spec.item,
            "qty": qty,
            "trend": spec.base_per_period * trend,
            "mock": True,
        }
    )
