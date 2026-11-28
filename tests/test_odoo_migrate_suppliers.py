"""Supplier consolidation plan (ADR 0019): pure, checked against the config."""
import importlib.util
import sys

import pytest

from conftest import BLG, ROOT
from ppsim.config import load_config

sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("odoo_migrate_suppliers", ROOT / "scripts" / "odoo_migrate_suppliers.py")
mig = importlib.util.module_from_spec(spec)
sys.modules["odoo_migrate_suppliers"] = mig
spec.loader.exec_module(mig)

OLD = list(mig.PARTNER_MAP)


@pytest.fixture(scope="module")
def cfg():
    return load_config(BLG)


def test_mapping_targets_exist_and_keep_items_they_supplied(cfg):
    for new, old in mig.SUCCESSOR_OF.items():
        assert new in cfg.suppliers and mig.PARTNER_MAP[old] == new
    assert set(mig.PARTNER_MAP.values()) - {None} == set(cfg.suppliers)
    # every old (supplier, item) line lands on a new supplier that supplies that item
    old_supplies = {"s_sugar": ["GLUCOSE", "SUCROSE"], "s_nutr": ["NH3", "AMSULF", "KPHOS", "MGSULF", "CACL2"],
                    "s_pack": ["BAG-25KG"], "s_memb": ["UFDF-MEMBRANE-SET"]}
    for old, new in mig.PARTNER_MAP.items():
        if new:
            for item in old_supplies[old.rsplit("_", 1)[0]]:
                assert item in cfg.suppliers[new].supplies, (old, new, item)


def test_suppliers_with_history_continue_one_to_one():
    with_history = ["s_sugar_a", "s_sugar_c", "s_nutr_c", "s_pack_b", "s_memb_a"]
    assert all(mig.SUCCESSOR_OF[mig.PARTNER_MAP[o]] == o for o in with_history)


def test_plan_renames_archives_moves_and_rekeys(cfg):
    names = {s.id: s.name for s in cfg.suppliers.values()}
    lines = ["supplierinfo:GLUCOSE:s_sugar_a", "supplierinfo:NH3:s_nutr_b", "supplierinfo:BAG-25KG:s_pack_a"]
    docs = {"purchase.order": ["hist:po:s_sugar_c:2025-08-04"], "account.move": ["hist:bill:s_nutr_c:2024-01-08",
                                                                                 "hist:inv:c_brands:2024-01-03"]}
    steps = mig.plan(names, {f"partner:{o}": True for o in OLD}, lines, docs)
    by = {(s.action, s.key): s for s in steps}
    assert len([s for s in steps if s.action == "rename"]) == 7
    assert len([s for s in steps if s.action == "archive"]) == 5
    assert by[("rename", "partner:s_sugar_a")].new_key == "partner:s_sweeteners"
    assert ("archive", "partner:s_pack_a") in by and ("archive", "partner:s_sugar_a") not in by
    assert by[("move_line", "supplierinfo:NH3:s_nutr_b")].new_key == "supplierinfo:NH3:s_broadline"
    assert ("delete_line", "supplierinfo:BAG-25KG:s_pack_a") in by
    assert by[("rekey", "hist:po:s_sugar_c:2025-08-04")].new_key == "hist:po:s_express:2025-08-04"
    assert by[("rekey", "hist:bill:s_nutr_c:2024-01-08")].new_key == "hist:bill:s_chemicals:2024-01-08"
    assert not any(s.key.startswith("hist:inv:") for s in steps)       # customer side untouched


def test_second_run_finds_nothing(cfg):
    names = {s.id: s.name for s in cfg.suppliers.values()}
    after = {f"partner:{n}": True for n in mig.SUCCESSOR_OF}
    after.update({f"partner:{o}": False for o in OLD if mig.PARTNER_MAP[o] is None
                  or mig.SUCCESSOR_OF[mig.PARTNER_MAP[o]] != o})           # archived, old key kept
    steps = mig.plan(names, after, ["supplierinfo:GLUCOSE:s_sweeteners"], {"purchase.order": ["hist:po:s_express:x"]})
    assert steps == []
