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


# --- M6 sourcing fixtures ---------------------------------------------------
# Hand-checkable numbers: item B should-cost = 10 material + 20% conversion
# + 10% margin = 13.20; three bidders quote 1.0x, 0.8x and 1.2x of it.

SOURCING_IDS = {
    "w_price": 0.5, "w_lt": 0.2, "w_q": 0.2, "w_risk": 0.1,
    "risk_lo": 0.9, "risk_md": 0.5, "risk_hi": 0.1,
    "conv_pct": 0.2, "margin_pct": 0.1, "base_b": 10,
    "fr_dom": 0, "duty_dom": 0, "fr_imp": 0.1, "duty_imp": 0.05,
    "carry": 0.2, "qcost": 2, "periods": 4, "drift": 0, "short_frac": 0.5,
    "dual_split": 0.5, "disr_prob": 1.0, "disr_weeks": 2, "fwd_weeks": 4, "z": 2,
    "p1": 1.0, "p2": 0.8, "p3": 1.2,
    "lt1": 0, "lt2": 1, "lt3": 2,
    "moq1": 1, "moq2": 2, "moq3": 4,
    "ppm1": 1000, "ppm2": 2000, "ppm3": 500,
    "otif1": 1.0, "otif2": 0.5, "otif3": 0.9,
    "sig1": 0, "sig2": 1, "sig3": 2,
    "ss1": 0, "ss2": 0.5, "ss3": 0.1,
}


def _quote(n: int) -> dict:
    return {
        "price_index": f"p{n}", "lead_time_delta": f"lt{n}", "moq_weeks": f"moq{n}",
        "quality_ppm": f"ppm{n}", "otif": f"otif{n}", "lead_time_sigma": f"sig{n}",
        "short_ship_rate": f"ss{n}",
    }


@pytest.fixture
def sourcing_registry(registry):
    reg = dict(registry)
    reg.update({k: A(k, v, "mock") for k, v in SOURCING_IDS.items()})
    return reg


@pytest.fixture
def sourcing_raw(minimal_raw):
    raw = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in minimal_raw.items()}
    raw["suppliers"] = [
        {"id": "s1", "name": "One (fictional)", "fictional": True, "archetype": "incumbent",
         "supplies": ["B"], "lane": "domestic", "incoterm": "DAP", "risk_tier": "low", "quote": _quote(1)},
        {"id": "s2", "name": "Two (fictional)", "fictional": True, "archetype": "low-cost",
         "supplies": ["B"], "lane": "import", "incoterm": "FOB", "risk_tier": "high", "quote": _quote(2)},
        {"id": "s3", "name": "Three (fictional)", "fictional": True, "archetype": "premium",
         "supplies": ["B"], "lane": "import", "incoterm": "DDP", "risk_tier": "medium", "quote": _quote(3)},
    ]
    raw["sourcing"] = {
        "weights": {"price": "w_price", "lead_time": "w_lt", "quality": "w_q", "risk": "w_risk"},
        "risk_scores": {"low": "risk_lo", "medium": "risk_md", "high": "risk_hi"},
        "lanes": {"domestic": {"freight_pct": "fr_dom", "duty_pct": "duty_dom"},
                  "import": {"freight_pct": "fr_imp", "duty_pct": "duty_imp"}},
        "should_cost": {"conversion_pct": "conv_pct", "margin_pct": "margin_pct", "material_base": {"B": "base_b"}},
        "carrying_cost_rate": "carry", "quality_cost_multiple": "qcost", "scorecard_periods": "periods",
        "price_drift_cv": "drift", "short_ship_fraction": "short_frac", "dual_source_split": "dual_split",
        "disruption_prob_base": "disr_prob", "disruption_weeks": "disr_weeks",
        "forward_buy_weeks": "fwd_weeks", "service_level_z": "z", "seed": 3,
    }
    return raw


@pytest.fixture
def sourcing_cfg(sourcing_raw, sourcing_registry):
    from ppsim.config import parse_config

    return parse_config(sourcing_raw, sourcing_registry)
