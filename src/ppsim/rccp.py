"""Rough-cut capacity planning (RCCP) with a bill of resources.

Each item in the bill of resources loads a resource with ``hours_per_unit`` for every
unit of its planned order *releases* (load is placed in the release week). Capacity per
week = units x hours_per_week x availability. Overloaded weeks are flagged.

Optional leveling pulls whole lots of a resource-loading item into earlier weeks with
spare capacity (at most ``max_pull`` weeks earlier, never before week 0). What can't be
pulled forward stays put and remains flagged. Pulling forward builds inventory early;
it never delays supply.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

_EPS = 1e-9


@dataclass(frozen=True)
class Resource:
    id: str
    name: str
    units: float
    hours_per_week: float
    availability: float

    @property
    def capacity_h(self) -> float:
        return self.units * self.hours_per_week * self.availability


@dataclass(frozen=True)
class BorLine:
    item: str
    resource: str
    hours_per_unit: float


def load_profile(
    releases: Mapping[str, Sequence[float]],
    bor: Sequence[BorLine],
    resources: Mapping[str, Resource],
    labels: Sequence,
) -> pd.DataFrame:
    """Long table: resource, period, load_h, capacity_h, utilization, overloaded."""
    h = len(labels)
    load: Dict[str, np.ndarray] = {r: np.zeros(h) for r in resources}
    for line in bor:
        if line.item in releases:
            load[line.resource] += np.asarray(releases[line.item], dtype=float) * line.hours_per_unit
    rows = []
    for rid, res in resources.items():
        cap = res.capacity_h
        for t, lab in enumerate(labels):
            rows.append({
                "resource": rid,
                "period": lab,
                "load_h": load[rid][t],
                "capacity_h": cap,
                "utilization": load[rid][t] / cap if cap > 0 else float("nan"),
                "overloaded": load[rid][t] > cap + 1e-6,
            })
    return pd.DataFrame(rows)


def level(
    releases: Sequence[float],
    hours_per_unit: float,
    capacity_h: float,
    lot: float,
    max_pull: int,
    other_load_h: Sequence[float] = (),
) -> Tuple[np.ndarray, List[str]]:
    """Pull whole lots earlier until each week fits capacity (where possible).

    ``other_load_h`` is load on the same resource from other items (kept fixed).
    Returns the leveled releases and notes describing each move or residual overload.
    """
    rel = np.asarray(releases, dtype=float).copy()
    h = len(rel)
    other = np.zeros(h) if len(other_load_h) == 0 else np.asarray(other_load_h, dtype=float)
    unit = lot if lot > 0 else None
    notes: List[str] = []

    def load(t: int) -> float:
        return rel[t] * hours_per_unit + other[t]

    for t in range(h):
        while load(t) > capacity_h + 1e-6 and rel[t] > _EPS:
            excess_h = load(t) - capacity_h
            chunk = unit if unit else excess_h / hours_per_unit
            if unit:
                chunk = min(chunk, rel[t])
            moved = False
            for s in range(t - 1, max(-1, t - max_pull - 1), -1):  # latest earlier week first
                spare = capacity_h - load(s)
                if spare + 1e-6 >= chunk * hours_per_unit:
                    rel[s] += chunk
                    rel[t] -= chunk
                    notes.append(f"moved {chunk:,.0f} from bucket {t} to bucket {s}")
                    moved = True
                    break
            if not moved:
                notes.append(f"bucket {t}: {excess_h:,.0f} h over capacity, no earlier slot within {max_pull} bucket(s)")
                break
    return rel, notes
