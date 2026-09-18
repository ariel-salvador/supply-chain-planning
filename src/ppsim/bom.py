"""Bill of materials: structure checks, low-level codes, multi-level explosion."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Sequence

import pandas as pd

from .config import BomLine


class BomError(ValueError):
    pass


def children(bom: Iterable[BomLine]) -> Dict[str, List[BomLine]]:
    out: Dict[str, List[BomLine]] = defaultdict(list)
    for line in bom:
        out[line.parent].append(line)
    return dict(out)


def low_level_codes(items: Sequence[str], bom: Sequence[BomLine]) -> Dict[str, int]:
    """Lowest level at which each item appears (0 = top). Raises on cycles.

    MRP must process items in increasing low-level code so that an item's gross
    requirements are complete before it is netted.
    """
    kids = children(bom)
    llc = {i: 0 for i in items}

    def visit(item: str, level: int, path: tuple) -> None:
        if item in path:
            raise BomError("BOM cycle: " + " -> ".join(path + (item,)))
        llc[item] = max(llc.get(item, 0), level)
        for line in kids.get(item, []):
            visit(line.component, level + 1, path + (item,))

    parents = {b.parent for b in bom}
    comps = {b.component for b in bom}
    roots = [i for i in items if i not in comps] or list(parents - comps)
    if bom and not roots:
        raise BomError("BOM has no root item (every item is a component): cycle")
    for r in roots:
        visit(r, 0, ())
    return llc


def reachable(root: str, bom: Sequence[BomLine]) -> List[str]:
    """Items in the BOM tree under ``root`` (including root), in low-level-code order."""
    kids = children(bom)
    seen: List[str] = []
    stack = [root]
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.append(i)
        stack.extend(l.component for l in kids.get(i, []))
    sub = [b for b in bom if b.parent in seen]
    llc = low_level_codes(seen, sub)
    return sorted(seen, key=lambda i: (llc[i], seen.index(i)))


def explode(root: str, bom: Sequence[BomLine], quantity: float = 1.0) -> pd.DataFrame:
    """Indented multi-level explosion of ``quantity`` units of ``root``.

    Returns one row per BOM path with columns
    level, parent, component, qty_per, extended_qty, qty_per_expr.
    """
    kids = children(bom)
    rows = []

    def walk(item: str, qty: float, level: int, path: tuple) -> None:
        if item in path:
            raise BomError("BOM cycle: " + " -> ".join(path + (item,)))
        for line in kids.get(item, []):
            ext = qty * line.qty_per
            rows.append(
                {
                    "level": level + 1,
                    "parent": item,
                    "component": line.component,
                    "qty_per": line.qty_per,
                    "extended_qty": ext,
                    "qty_per_expr": line.expr,
                }
            )
            walk(line.component, ext, level + 1, path + (item,))

    walk(root, quantity, 0, ())
    return pd.DataFrame(rows, columns=["level", "parent", "component", "qty_per", "extended_qty", "qty_per_expr"])


def total_requirements(root: str, bom: Sequence[BomLine], quantity: float = 1.0) -> Dict[str, float]:
    """Summed-up requirement of every component for ``quantity`` of ``root``."""
    df = explode(root, bom, quantity)
    return df.groupby("component")["extended_qty"].sum().to_dict() if len(df) else {}
