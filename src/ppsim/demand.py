"""Seeded mock demand generator.

Demand is synthetic by design: trend x seasonality x noise around a base rate. Output
always carries ``mock=True`` so nothing downstream can mistake it for real data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DemandSpec


def periods(start: str, horizon: int, freq: str) -> pd.PeriodIndex:
    return pd.period_range(start=start, periods=horizon, freq=freq)


def generate(spec: DemandSpec, index: pd.PeriodIndex) -> pd.DataFrame:
    """Generate demand for ``spec.item`` over ``index``.

    - trend: compound ``annual_growth`` applied continuously from the first period
    - seasonality: cosine with amplitude ``seasonal_amplitude`` (fraction of base),
      peaking in ``seasonal_peak_month``
    - noise: multiplicative normal with coefficient of variation ``noise_cv``,
      reproducible via ``seed``; quantities are clipped at zero
    """
    start = index[0].start_time
    mid = index.start_time + (index.end_time - index.start_time) / 2
    years = np.asarray((mid - start).days, dtype=float) / 365.25
    trend = (1.0 + spec.annual_growth) ** years

    # fractional month of year at each period's midpoint (1.0 = Jan 1)
    month_pos = np.asarray(mid.month, dtype=float) + (np.asarray(mid.day, dtype=float) - 1) / 30.4
    season = 1.0 + spec.seasonal_amplitude * np.cos(2 * np.pi * (month_pos - spec.seasonal_peak_month - 0.5) / 12)

    rng = np.random.default_rng(spec.seed)
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
