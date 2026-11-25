import numpy as np

from ppsim.config import DemandSpec
from ppsim.demand import generate, periods


def test_deterministic_and_labeled_mock():
    spec = DemandSpec("A", True, 100, annual_growth=0.1, seasonal_amplitude=0.2, noise_cv=0.1, seed=7)
    idx = periods("2027-01-04", 52, "W-SUN")
    a, b = generate(spec, idx), generate(spec, idx)
    assert a["qty"].equals(b["qty"])
    assert a["mock"].all() and len(a) == 52
    assert (a["qty"] >= 0).all()


def test_flat_spec_is_flat():
    idx = periods("2027-01", 12, "M")
    df = generate(DemandSpec("A", True, 50), idx)
    assert np.allclose(df["qty"], 50)


def test_seasonal_peak_month():
    spec = DemandSpec("A", True, 100, seasonal_amplitude=0.3, seasonal_peak_month=7)
    df = generate(spec, periods("2027-01", 12, "M"))
    assert df["qty"].idxmax() == 6  # July
    assert df["qty"].max() > 129


def test_anchor_backcasts_trend_into_the_plan_base():
    spec = DemandSpec("A", True, 100, annual_growth=0.15)
    hist = generate(spec, periods("2024-01-01", 156, "W-SUN"), anchor="2027-01-04")
    # three years before the anchor the trend is base / 1.15^3, and it rises toward base
    assert abs(hist["trend"].iloc[0] - 100 / 1.15 ** 3) < 0.5
    assert hist["trend"].is_monotonic_increasing and hist["trend"].iloc[-1] < 100


def test_default_anchor_and_seed_unchanged():
    spec = DemandSpec("A", True, 100, annual_growth=0.15, noise_cv=0.1, seed=42)
    idx = periods("2027-01-04", 26, "W-SUN")
    assert generate(spec, idx)["qty"].equals(generate(spec, idx, anchor="2027-01-04", seed=42)["qty"])
    assert not generate(spec, idx)["qty"].equals(generate(spec, idx, seed=7)["qty"])
