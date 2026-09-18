from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLG = ROOT / "products" / "blg_whey_protein" / "product.yaml"


@pytest.fixture
def minimal_raw():
    """Smallest valid config: A <- 2 x B, with one cited parameter."""
    return {
        "product": {"id": "t", "name": "test"},
        "time": {"freq": "W-SUN", "start": "2027-01-04", "horizon": 5},
        "sources": {"s1": {"citation": "Test source", "url": "https://example.org"}},
        "parameters": {"k": {"value": 2, "unit": "kg/kg", "source": "s1", "locator": "p. 1"}},
        "derived": {"k2": {"expr": "k * 2"}},
        "items": [
            {"id": "A", "type": "finished", "uom": "kg"},
            {"id": "B", "type": "purchased", "uom": "kg", "planning": {"lead_time": "k - 1"}},
        ],
        "bom": [{"parent": "A", "component": "B", "qty_per": "k"}],
        "demand": {"mock": True, "item": "A", "base_per_period": 10},
    }
