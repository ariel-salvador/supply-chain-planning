"""Assumptions registry: every model number lives in ``knowledge/assumptions.csv``.

Each row is labeled ``cited`` (public source), ``estimate`` (reasoned, with basis
given in ``source``) or ``mock`` (illustrative). Product configs reference rows by id.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

COLUMNS = ["id", "name", "value", "unit", "low", "high", "source", "url", "retrieved", "confidence", "status", "used_in"]
STATUSES = ("cited", "estimate", "mock")
CONFIDENCE = ("high", "med", "low")


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class Assumption:
    id: str
    name: str
    value: float
    unit: str
    low: Optional[float]
    high: Optional[float]
    source: str
    url: str
    retrieved: str
    confidence: str
    status: str
    used_in: Tuple[str, ...]


def _num(s: str, where: str) -> Optional[float]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        raise RegistryError(f"{where}: not a number: {s!r}") from None


def row_problems(row: Dict[str, str]) -> List[str]:
    """Labeling / citation problems for one CSV row (empty list = OK)."""
    p = []
    rid = row.get("id") or "?"
    status = (row.get("status") or "").strip()
    if status not in STATUSES:
        p.append(f"{rid}: status must be one of {STATUSES} (got {status!r})")
    if (row.get("confidence") or "").strip() not in CONFIDENCE:
        p.append(f"{rid}: confidence must be one of {CONFIDENCE}")
    if not (row.get("unit") or "").strip():
        p.append(f"{rid}: missing unit")
    if not (row.get("source") or "").strip():
        p.append(f"{rid}: missing source (for estimates: the basis; for mock: say 'mock ...')")
    if status == "cited" and not (row.get("retrieved") or "").strip():
        p.append(f"{rid}: cited value needs a retrieved date")
    if status == "cited" and not (row.get("url") or "").strip() and not (row.get("source") or "").lower().startswith("definition"):
        p.append(f"{rid}: cited value needs a url (unless it is a unit definition)")
    if status == "mock" and "mock" not in (row.get("source") or "").lower():
        p.append(f"{rid}: mock value must say 'mock' in source")
    return p


def load_registry(path: Union[str, Path]) -> Dict[str, Assumption]:
    path = Path(path)
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise RegistryError(f"{path}: columns must be {COLUMNS}, got {reader.fieldnames}")
        out: Dict[str, Assumption] = {}
        problems: List[str] = []
        for i, row in enumerate(reader, start=2):
            rid = (row["id"] or "").strip()
            where = f"{path.name}:{i}"
            if not rid:
                problems.append(f"{where}: missing id")
                continue
            if rid in out:
                problems.append(f"{where}: duplicate id {rid!r}")
                continue
            problems += [f"{where}: {m}" for m in row_problems(row)]
            value = _num(row["value"], where)
            if value is None:
                problems.append(f"{where}: {rid}: missing value")
                continue
            out[rid] = Assumption(
                id=rid,
                name=row["name"].strip(),
                value=value,
                unit=row["unit"].strip(),
                low=_num(row["low"], where),
                high=_num(row["high"], where),
                source=row["source"].strip(),
                url=row["url"].strip(),
                retrieved=row["retrieved"].strip(),
                confidence=row["confidence"].strip(),
                status=row["status"].strip(),
                used_in=tuple(u.strip() for u in (row["used_in"] or "").split(";") if u.strip()),
            )
    if problems:
        raise RegistryError("assumptions registry problems:\n  " + "\n  ".join(problems))
    return out
