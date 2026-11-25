import pandas as pd
import pytest

from ppsim import fred
from ppsim.pipeline import run, write_outputs
from conftest import BLG


@pytest.fixture
def fake_prices(monkeypatch):
    idx = pd.to_datetime(["2026-01-01", "2026-02-01"])
    data = {"PMAIZMTUSDM": pd.Series([200.0, 220.0], index=idx), "PSUGAISAUSDM": pd.Series([15.0, 16.0], index=idx)}
    for ppi in ("PCU325311325311", "PCU325180325180", "PCU322220322220", "PCU326199326199"):
        data[ppi] = pd.Series(100.0, index=idx)   # flat producer price indices

    def fake(sid, **k):
        if sid not in data:
            raise fred.FredError(f"{sid} not in the test sample")
        return data[sid]

    monkeypatch.setattr(fred, "fetch_series", fake)
    monkeypatch.setattr(fred, "cache_metadata", lambda sid, *a: {"series": sid})


def test_end_to_end_blg(tmp_path, fake_prices):
    res = run(BLG)
    assert {"BLG-PWD", "BLG-FERM", "GLUCOSE", "NH3", "BAG-25KG", "UFDF-MEMBRANE-SET"} <= set(res.mrp)
    assert "SUCROSE" not in res.mrp  # not in the active BOM
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


def test_sop_mps_drive_mrp(fake_prices):
    res = run(BLG)
    assert res.sop is not None and res.mps is not None
    t = res.mps.table
    fg = res.mrp["BLG-PWD"].table
    # MPS planned quantities are the finished item's MRP planned receipts
    assert fg.loc["planned_order_receipts"].tolist() == pytest.approx(t.loc["planned_mps"].tolist())
    assert fg.loc["gross_requirements"].tolist() == pytest.approx(t.loc["projected_demand"].tolist())
    # nothing planned inside the planning time fence
    ptf = res.cfg.mps.planning_time_fence
    assert t.loc["planned_mps"].iloc[:ptf].sum() == 0
    # MPS within weekly capacity, and the base case raises no warnings
    load = t.loc["planned_mps"] + t.loc["firm_mps"]
    assert (load <= res.cfg.sop.capacity_per_week + 1e-6).all()
    assert res.warnings == []
    # S&OP: 12 months, chase meets target, fermentation in whole batches
    assert len(res.sop) == 12 and not res.sop["below_target"].any()
    rel = res.mrp["BLG-FERM"].table.loc["planned_order_receipts"]
    batch = res.cfg.derived["batch_rblg_kg"]
    assert ((rel / batch) % 1 < 1e-9).all()


def test_sop_outputs_written(tmp_path, fake_prices):
    files = {p.name for p in write_outputs(run(BLG), tmp_path)}
    assert {"sop_plan.csv", "mps_BLG-PWD.csv"} <= files


def test_rccp_leveling_removes_fermenter_overload():
    res = run(BLG, fetch_prices=False)
    assert res.rccp_before["overloaded"].any()          # whole-batch rounding overloads a week
    assert not res.rccp["overloaded"].any()             # leveling fixes it
    assert res.rccp_moves and all(m.startswith("BLG-FERM: moved") for m in res.rccp_moves)
    # leveling only moves batches earlier: total fermentation volume unchanged
    before = res.rccp_before["load_h"].sum()
    assert res.rccp["load_h"].sum() == pytest.approx(before)
    # components follow the leveled schedule, and nothing goes short
    assert res.warnings == []


def test_po_schedule_and_spend(fake_prices):
    res = run(BLG)
    po = res.po_lines
    # every purchased item in the active BOM is ordered from its (fictional) vendor
    assert set(po["vendor"]).issubset({s.name for s in res.cfg.suppliers.values()})
    # POs go to the supplier the RFQ awarded (M6), not to a fixed vendor list
    awarded = {i: r["awarded_name"] for i, r in res.awards.iterrows()}
    assert all(awarded[r.item] == r.vendor for r in po.itertuples())
    assert (po["due_bucket"] - po["order_bucket"] >= 0).all()
    # PO quantities equal MRP planned releases for each purchased item
    for item, q in po.groupby("item")["qty"].sum().items():
        assert q == pytest.approx(res.mrp[item].table.loc["planned_order_releases"].sum())
    # glucose is priced (corn link), nutrients/bags are excluded rather than guessed
    assert "GLUCOSE" in res.spend.index and "NH3" in res.spend_excluded
    s = res.spend.loc["GLUCOSE"]
    assert s["low_p10"] <= s["median_p50"] <= s["high_p90"]
