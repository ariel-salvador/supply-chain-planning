import numpy as np
import pandas as pd
import pytest

from ppsim.purchasing import SCENARIOS, price_scenarios, spend


def prices():
    idx = pd.date_range("2016-01-01", periods=120, freq="MS")
    return pd.DataFrame({"X": np.arange(1, 121, dtype=float)}, index=idx)  # 1..120


def test_price_scenarios_window_and_percentiles():
    sc = price_scenarios(prices(), window_years=5)
    row = sc.loc["X"]
    assert row["base"] == 120 and row["base_date"] == "2025-12"
    window = np.arange(61, 121)  # last 60 months
    assert row["median_p50"] == pytest.approx(np.percentile(window, 50))
    assert row["low_p10"] < row["median_p50"] < row["high_p90"]
    assert [n for n, _ in SCENARIOS] == ["low_p10", "median_p50", "high_p90"]


def test_spend_prices_known_items_and_excludes_others():
    sched = pd.DataFrame({"po": ["P1", "P1", "P2"], "item": ["X", "Y", "X"], "qty": [10.0, 5.0, 2.0]})
    sc = price_scenarios(prices(), window_years=5)
    lines, totals, excluded = spend(sched, sc)
    assert excluded == ["Y"]
    assert lines.loc[lines.item == "X", "amount_usd"].tolist() == [1200, 240]
    assert np.isnan(lines.loc[lines.item == "Y", "amount_usd"]).all()
    assert totals.loc["X", "base"] == 12 * 120
    assert totals.loc["TOTAL (priced items)", "base"] == 12 * 120
