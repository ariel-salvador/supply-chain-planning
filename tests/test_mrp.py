import numpy as np
import pytest

from ppsim.config import BomLine, LotSizing, Planning
from ppsim.mrp import lot_size, mrp_item, run_mrp, to_long

LABELS = list(range(5))
GROSS = np.array([10, 15, 20, 5, 25], dtype=float)


def plan(**kw):
    kw.setdefault("lead_time", 2)
    kw.setdefault("on_hand", 20)
    kw.setdefault("scheduled_receipts", {1: 10})
    return Planning(**kw)


def row(rec, name):
    return rec.table.loc[name].tolist()


def test_lot_for_lot_textbook():
    rec = mrp_item("A", GROSS, plan(), LABELS)
    assert row(rec, "projected_on_hand") == [10, 5, 0, 0, 0]
    assert row(rec, "net_requirements") == [0, 0, 15, 5, 25]
    assert row(rec, "planned_order_receipts") == [0, 0, 15, 5, 25]
    assert row(rec, "planned_order_releases") == [15, 5, 25, 0, 0]
    assert rec.past_due_release == 0 and not rec.warnings


def test_fixed_order_quantity():
    rec = mrp_item("A", GROSS, plan(lot_sizing=LotSizing("fixed_order_quantity", quantity=30)), LABELS)
    assert row(rec, "planned_order_receipts") == [0, 0, 30, 0, 30]
    assert row(rec, "projected_on_hand") == [10, 5, 15, 10, 15]
    assert row(rec, "planned_order_releases") == [30, 0, 30, 0, 0]


def test_periods_of_supply():
    rec = mrp_item("A", GROSS, plan(lot_sizing=LotSizing("periods_of_supply", periods=2)), LABELS)
    assert row(rec, "planned_order_receipts") == [0, 0, 20, 0, 25]
    assert row(rec, "projected_on_hand") == [10, 5, 5, 0, 0]


def test_safety_stock_is_protected():
    rec = mrp_item("A", GROSS, plan(safety_stock=5), LABELS)
    assert row(rec, "net_requirements") == [0, 0, 20, 5, 25]
    assert min(row(rec, "projected_on_hand")) >= 5


def test_min_and_multiple():
    lot = LotSizing("lot_for_lot", minimum=12, multiple=5)
    assert lot_size(3, lot) == 15
    assert lot_size(16, lot) == 20
    assert lot_size(0, lot) == 0


def test_past_due_release_is_flagged():
    rec = mrp_item("A", np.array([30, 0, 0, 0, 0.0]), Planning(lead_time=2), LABELS)
    assert rec.past_due_release == 30
    assert any("before the horizon" in w for w in rec.warnings)


def test_multilevel_dependent_demand_and_past_due_propagation():
    items = {"X": Planning(lead_time=1), "C": Planning(lead_time=0)}
    bom = [BomLine("X", "C", 3.0, "3")]
    recs = run_mrp(items, bom, {"X": [5, 10, 0, 0, 0]}, LABELS)
    # X: receipts [5,10,...] -> releases [10,0,...] plus 5 past due charged to bucket 0
    assert recs["X"].past_due_release == 5
    assert row(recs["C"], "gross_requirements") == [45, 0, 0, 0, 0]


def test_run_mrp_rejects_bad_inputs():
    with pytest.raises(KeyError):
        run_mrp({"X": Planning()}, [], {"Y": [0] * 5}, LABELS)
    with pytest.raises(ValueError):
        run_mrp({"X": Planning()}, [], {"X": [0] * 3}, LABELS)


def test_to_long_shape():
    recs = run_mrp({"X": Planning()}, [], {"X": [1, 2, 3, 4, 5]}, LABELS)
    df = to_long(recs)
    assert len(df) == 6 * 5 and set(df.columns) == {"item", "period", "row", "qty"}
