from pathlib import Path

import pytest

from ppsim.registry import Assumption

ROOT = Path(__file__).resolve().parents[1]
BLG = ROOT / "products" / "blg_whey_protein.yaml"
REGISTRY = ROOT / "knowledge" / "assumptions.csv"


def A(id, value, status="cited", used_in=("t",)):
    return Assumption(id, id, float(value), "kg", None, None, "src" if status != "mock" else "mock", "https://x", "2026-01-01", "med", status, tuple(used_in))


@pytest.fixture
def registry():
    return {a.id: a for a in [A("k", 2), A("c3", 3), A("m_lt", 1, "mock"), A("m_base", 10, "mock"), A("m_oh", 5, "mock"), A("other", 1, used_in=("x",))]}


@pytest.fixture
def minimal_raw():
    """Smallest valid config: A <- k x B."""
    return {
        "product": {"id": "t", "name": "test"},
        "time": {"freq": "W-SUN", "start": "2027-01-04", "horizon": 5},
        "derived": {"k2": "k * c3"},
        "items": [
            {"id": "A", "type": "finished", "uom": "kg", "planning": {"on_hand": "m_oh"}},
            {"id": "B", "type": "purchased", "uom": "kg", "planning": {"lead_time": "m_lt"}},
        ],
        "bom": [{"parent": "A", "component": "B", "qty_per": "k"}],
        "demand": {"mock": True, "item": "A", "base_per_period": "m_base"},
    }
