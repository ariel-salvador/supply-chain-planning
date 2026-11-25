"""The backfill's step plan (pure): every document's steps, in the order they happened."""
import importlib.util
import sys

import pandas as pd
import pytest

from conftest import ROOT
from test_history import case  # noqa: F401  (module-scoped ledger fixture)

sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("odoo_history", ROOT / "scripts" / "odoo_history.py")
oh = importlib.util.module_from_spec(spec)
sys.modules["odoo_history"] = oh
spec.loader.exec_module(oh)


@pytest.fixture(scope="module")
def plan(case):  # noqa: F811
    _, _, _, hist = case
    return hist, oh.actions(hist)


def test_steps_are_chronological_and_opening_comes_first(plan):
    hist, acts = plan
    assert [a.sort_key for a in acts] == sorted(a.sort_key for a in acts)
    moves = [a for a in acts if a.kind in ("opening", "receipt", "mo", "scrap", "delivery")]
    assert moves[0].kind == "opening" and moves[0].when < hist.weeks[0]   # orders may be placed earlier
    assert all(a.when <= hist.end + pd.Timedelta(hours=12) for a in acts)


def test_counts_match_the_ledger(plan):
    hist, acts = plan
    n = oh.summary(acts)
    assert n["so"] == len(hist.sales) and n["delivery"] == n["invoice"] == hist.sales["date_shipped"].notna().sum()
    assert n["pay_in"] == hist.sales["date_paid"].notna().sum()
    assert n["po"] == hist.purchases["key"].nunique()
    assert n["mo"] == len(hist.production) and n["scrap"] == int(hist.production["scrapped"].sum())


@pytest.mark.parametrize("chain", [("so", "delivery", "invoice", "pay_in"), ("po", "receipt", "bill", "pay_out")])
def test_each_document_moves_through_its_states_in_order(plan, chain):
    _, acts = plan
    pos = {}
    for n, a in enumerate(acts):
        if a.kind in chain:
            pos.setdefault(a.key, []).append((chain.index(a.kind), n))
    assert pos
    for key, steps in pos.items():
        stages = [s for s, _ in sorted(steps, key=lambda x: x[1])]
        assert stages == list(range(len(stages))), key       # no step skipped or out of order


def test_stock_arrives_before_it_is_used_the_same_day(plan):
    _, acts = plan
    assert oh.RANK["receipt"] < oh.RANK["mo"] < oh.RANK["delivery"]
    assert oh.RANK["po"] < oh.RANK["receipt"] < oh.RANK["bill"] < oh.RANK["pay_out"]


def test_powder_runs_only_convert_finished_fermentation(plan):
    hist, _ = plan
    p = hist.production
    ferm_done = p[(p["product"] == "BLG-FERM") & ~p["scrapped"]].set_index("batch")["date_finished"]
    for r in p[p["product"] == "BLG-PWD"].itertuples():
        assert ferm_done[r.batch] < r.date_start
