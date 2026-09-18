import pandas as pd
import pytest

from ppsim import fred
from ppsim.pipeline import run, write_outputs
from conftest import BLG


@pytest.fixture
def fake_prices(monkeypatch):
    idx = pd.to_datetime(["2026-01-01", "2026-02-01"])
    data = {"PMAIZMTUSDM": pd.Series([200.0, 220.0], index=idx), "PSUGAISAUSDM": pd.Series([15.0, 16.0], index=idx)}
    monkeypatch.setattr(fred, "fetch_series", lambda sid, **k: data[sid])
    monkeypatch.setattr(fred, "cache_metadata", lambda sid, *a: {"series": sid})


def test_end_to_end_blg(tmp_path, fake_prices):
    res = run(BLG)
    assert set(res.mrp) == {"BLG-PWD", "BLG-FERM", "GLUCOSE"}  # SUCROSE not in active BOM
    # every planned release of powder becomes fermentation gross requirement x qty_per
    pwd_rel = res.mrp["BLG-PWD"].table.loc["planned_order_releases"]
    ferm_gross = res.mrp["BLG-FERM"].table.loc["gross_requirements"]
    assert ferm_gross.sum() == pytest.approx(pwd_rel.sum() * res.cfg.derived["rblg_kg_per_kg_product"])
    # feedstock cost = corn price / 1000 * corn per glucose * glucose per powder
    per_kg = res.cfg.derived["corn_kg_per_glucose_kg"] * res.cfg.derived["sugar_kg_per_kg_rblg"] * res.cfg.derived["rblg_kg_per_kg_product"]
    assert res.feedstock_cost["total"].iloc[0] == pytest.approx(0.2 * per_kg)

    files = {p.name for p in write_outputs(res, tmp_path)}
    assert {"demand_mock.csv", "mrp_long.csv", "manifest.json", "parameters.csv"} <= files


def test_sucrose_variant(fake_prices):
    res = run(BLG, variant="sucrose")
    assert "SUCROSE" in res.mrp and "GLUCOSE" not in res.mrp
    assert list(res.feedstock_cost.columns) == ["SUCROSE", "total"]


def test_prices_optional():
    res = run(BLG, fetch_prices=False)
    assert res.prices is None and res.feedstock_cost is None
