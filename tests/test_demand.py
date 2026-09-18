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
