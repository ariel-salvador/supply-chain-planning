"""One-off: consolidate the supplier master in the live ERP, 12 -> 7 suppliers (ADR 0019).

    .venv/bin/python scripts/odoo_migrate_suppliers.py            # dry run: print the plan
    .venv/bin/python scripts/odoo_migrate_suppliers.py --apply    # write it (back up first)

Only records the scripts made (they carry a ``x_pps_key``) are touched:

- **partners:** for each new supplier, one old record is renamed and re-keyed in place,
  so its purchase history (orders, receipts, bills, payments) follows it. The other old
  records are archived, never deleted;
- **vendor price lists:** each old line moves to its new supplier and key; the two lines
  of retired suppliers (no successor for that item) are deleted. This is the one
  deliberate exception to "scripts never delete", approved for this migration;
- **history keys:** purchase orders and vendor bills from the backfill are re-keyed to
  the new supplier ids, so the history stays reproducible from the config.

Afterwards ``make odoo-live-master`` shows (and with ``APPLY_DIFFS=1`` applies) the new
prices, minimums, lead times, preferred order, tags and kanban levels. Idempotent: a
second run finds nothing left to do.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import PPS_KEY, Odoo, OdooError  # noqa: E402

# old supplier id -> new supplier id (None: retired). Reviewed with the user 2026-11-27.
PARTNER_MAP: Dict[str, Optional[str]] = {
    "s_sugar_a": "s_sweeteners", "s_sugar_b": "s_broadline", "s_sugar_c": "s_express",
    "s_nutr_a": "s_express", "s_nutr_b": "s_broadline", "s_nutr_c": "s_chemicals",
    "s_pack_a": None, "s_pack_b": "s_packaging", "s_pack_c": "s_express",
    "s_memb_a": "s_filtration", "s_memb_b": "s_aftermarket", "s_memb_c": None,
}
# the old record each new supplier continues (keeps its history); every other old one is archived
SUCCESSOR_OF: Dict[str, str] = {
    "s_sweeteners": "s_sugar_a", "s_chemicals": "s_nutr_c", "s_packaging": "s_pack_b",
    "s_filtration": "s_memb_a", "s_broadline": "s_sugar_b", "s_express": "s_sugar_c",
    "s_aftermarket": "s_memb_b",
}


@dataclass(frozen=True)
class Step:
    action: str          # rename | archive | move_line | delete_line | rekey
    model: str
    key: str             # current x_pps_key
    new_key: str = ""
    vals: tuple = ()     # ((field, value), ...); partner ids resolved at apply time

    def describe(self) -> str:
        extra = f" -> {self.new_key}" if self.new_key else ""
        v = ", ".join(f"{k}={val}" for k, val in self.vals if k != "partner_key")
        return f"{self.action:11s} {self.model:22s} {self.key}{extra}{'  ' + v if v else ''}"


def rekey(key: str) -> Optional[str]:
    """New x_pps_key for a history document key (hist:po:<sup>:<date>, hist:bill:<sup>:<date>)."""
    parts = key.split(":")
    if len(parts) >= 3 and parts[0] == "hist" and parts[1] in ("po", "bill") and parts[2] in PARTNER_MAP:
        new = PARTNER_MAP[parts[2]]
        if new is None:
            raise ValueError(f"{key}: history of a retired supplier has no successor")
        return ":".join([parts[0], parts[1], new, *parts[3:]])
    return None


def plan(names: Dict[str, str], partners: Dict[str, bool], line_keys: List[str],
         doc_keys: Dict[str, List[str]]) -> List[Step]:
    """Every write still needed, from what exists now.

    ``names``: new supplier id -> name (config); ``partners``: x_pps_key -> active.
    """
    steps: List[Step] = []
    have = set(partners)
    for new, old in SUCCESSOR_OF.items():
        if f"partner:{old}" in have and f"partner:{new}" not in have:
            steps.append(Step("rename", "res.partner", f"partner:{old}", f"partner:{new}", (("name", names[new]),)))
    for old, new in PARTNER_MAP.items():
        if partners.get(f"partner:{old}") and SUCCESSOR_OF.get(new or "") != old:
            steps.append(Step("archive", "res.partner", f"partner:{old}"))
    for key in line_keys:                           # supplierinfo:<item>:<supplier>
        _, item, sup = key.split(":", 2)
        if sup not in PARTNER_MAP:
            continue
        new = PARTNER_MAP[sup]
        if new is None:
            steps.append(Step("delete_line", "product.supplierinfo", key))
        else:
            steps.append(Step("move_line", "product.supplierinfo", key, f"supplierinfo:{item}:{new}",
                              (("partner_key", f"partner:{new}"),)))
    for model, keys in doc_keys.items():
        for key in keys:
            nk = rekey(key)
            if nk and nk != key:
                steps.append(Step("rekey", model, key, nk))
    return steps


def apply(o: Odoo, steps: Sequence[Step]) -> Dict[str, int]:
    done: Dict[str, int] = {}
    ids: Dict[str, int] = {}

    def rid(model: str, key: str) -> int:
        rows = o.search_read(model, [[PPS_KEY, "=", key], ["active", "in", [True, False]]]
                             if model == "res.partner" else [[PPS_KEY, "=", key]], ["id"], limit=2)
        if len(rows) != 1:
            raise OdooError(f"{model}: expected one record with key {key!r}, found {len(rows)}")
        return rows[0]["id"]

    for s in steps:
        target = rid(s.model, s.key)
        vals = dict(s.vals)
        if s.action == "rename":
            o.write(s.model, [target], {"name": vals["name"], PPS_KEY: s.new_key})
        elif s.action == "archive":
            o.write(s.model, [target], {"active": False})
        elif s.action == "move_line":
            pk = vals["partner_key"]
            ids.setdefault(pk, rid("res.partner", pk))
            o.write(s.model, [target], {"partner_id": ids[pk], PPS_KEY: s.new_key})
        elif s.action == "delete_line":
            o.call(s.model, "unlink", ids=[target])
        elif s.action == "rekey":
            o.write(s.model, [target], {PPS_KEY: s.new_key})
        done[s.action] = done.get(s.action, 0) + 1
    return done


def read_state(o: Odoo):
    parts = o.search_read("res.partner", [[PPS_KEY, "like", "partner:s_"], ["active", "in", [True, False]]],
                          [PPS_KEY, "active"])
    lines = o.search_read("product.supplierinfo", [[PPS_KEY, "like", "supplierinfo:"]], [PPS_KEY])
    docs = {m: [r[PPS_KEY] for r in o.search_read(m, [[PPS_KEY, "like", "hist:"]], [PPS_KEY])]
            for m in ("purchase.order", "account.move")}
    return {p[PPS_KEY]: p["active"] for p in parts}, [ln[PPS_KEY] for ln in lines], docs


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the plan (take a backup first)")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT / "src"))
    from ppsim.config import load_config
    cfg = load_config(ROOT / "products" / "blg_whey_protein.yaml")
    names = {s.id: s.name for s in cfg.suppliers.values()}
    missing = set(SUCCESSOR_OF) - set(names)
    if missing:
        raise SystemExit(f"config lacks new suppliers {sorted(missing)}")
    o = Odoo.live()
    steps = plan(names, *read_state(o))
    counts: Dict[str, int] = {}
    for s in steps:
        counts[s.action] = counts.get(s.action, 0) + 1
    print(f"{o.db}: {len(steps)} step(s) {counts}")
    for s in steps:
        if s.action != "rekey":
            print("  " + s.describe())
    if counts.get("rekey"):
        print(f"  rekey       {counts['rekey']} history purchase orders and bills to the new supplier ids")
    if not args.apply:
        print("dry run: nothing written (rerun with --apply)")
        return 0
    print(f"applied: {apply(o, steps)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooError as e:
        print(f"odoo error: {e}", file=sys.stderr)
        sys.exit(1)
