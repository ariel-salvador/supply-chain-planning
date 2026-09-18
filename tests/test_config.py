import copy

import pytest

from ppsim.config import ConfigError, apply_variant, evaluate, expr_names, load_config, parse_config
from conftest import BLG


def test_minimal_config_parses(minimal_raw, registry):
    cfg = parse_config(minimal_raw, registry)
    assert cfg.derived["k2"] == 6
    assert cfg.bom[0].qty_per == 2
    assert cfg.items["B"].planning.lead_time == 1
    assert cfg.items["A"].planning.on_hand == 5
    assert set(cfg.assumptions) == {"k", "c3", "m_lt", "m_base", "m_oh"}


def test_raw_planning_number_rejected(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["items"][0]["planning"]["on_hand"] = 500
    with pytest.raises(ConfigError, match="raw number"):
        parse_config(raw, registry)


def test_zero_is_allowed_literally(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["items"][0]["planning"]["safety_stock"] = 0
    assert parse_config(raw, registry).items["A"].planning.safety_stock == 0


@pytest.mark.parametrize("expr", ["k * 2", "k / 1000", "0.5 * k"])
def test_numeric_literals_in_expressions_rejected(minimal_raw, registry, expr):
    raw = copy.deepcopy(minimal_raw)
    raw["bom"][0]["qty_per"] = expr
    with pytest.raises(ConfigError, match="literal"):
        parse_config(raw, registry)


def test_bom_quantity_must_rest_on_cited(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["bom"][0]["qty_per"] = "k * m_lt"
    with pytest.raises(ConfigError, match="cited"):
        parse_config(raw, registry)


def test_bom_quantity_via_derived_mock_rejected(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["derived"]["bad"] = "k * m_base"
    raw["bom"][0]["qty_per"] = "bad"
    with pytest.raises(ConfigError, match="m_base"):
        parse_config(raw, registry)


def test_unknown_assumption_id(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["bom"][0]["qty_per"] = "nope"
    with pytest.raises(ConfigError, match="unknown assumption"):
        parse_config(raw, registry)


def test_used_in_must_list_product(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["bom"][0]["qty_per"] = "other"
    with pytest.raises(ConfigError, match="used_in"):
        parse_config(raw, registry)


def test_demand_must_be_explicitly_mock(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["demand"]["mock"] = False
    with pytest.raises(ConfigError, match="mock"):
        parse_config(raw, registry)


def test_fractional_lead_time_is_rejected(minimal_raw, registry):
    raw = copy.deepcopy(minimal_raw)
    raw["items"][1]["planning"]["lead_time"] = "m_lt / c3"
    with pytest.raises(ConfigError, match="whole number"):
        parse_config(raw, registry)


@pytest.mark.parametrize(
    "expr, expected",
    [("a * (b + 2)", 6.0), ("-a ** 2", -4.0), ("ceil(b / 2)", 1.0), ("max(a, b) / min(a, b)", 2.0), (3, 3.0)],
)
def test_evaluate(expr, expected):
    assert evaluate(expr, {"a": 2, "b": 1}) == expected


@pytest.mark.parametrize("expr", ["__import__('os')", "a.b", "open('x')", "a if a else b", "[1]"])
def test_evaluate_rejects_non_arithmetic(expr):
    with pytest.raises(ConfigError):
        evaluate(expr, {"a": 1, "b": 2})


def test_expr_names_excludes_functions():
    assert expr_names("ceil(a / b) + max(a, c)") == {"a", "b", "c"}


def test_blg_config_loads_and_labels():
    cfg = load_config(BLG)
    statuses = {a.status for a in cfg.assumptions.values()}
    assert statuses == {"cited", "mock"}
    assert cfg.demand.mock is True


def test_blg_derived_values():
    cfg = load_config(BLG)
    d = cfg.derived
    assert d["rblg_kg_per_kg_product"] == pytest.approx(0.858 / 0.975)
    assert d["sugar_kg_per_kg_rblg"] == pytest.approx(1 / (0.223 * 0.90))
    assert d["corn_kg_per_glucose_kg"] == pytest.approx((25 / 14) * 162.141 / 180.156)
    assert cfg.items["BLG-FERM"].planning.lead_time == 1  # 144 h cycle -> 1 week
    assert cfg.items["BLG-PWD"].planning.on_hand == 60000


def test_variant_substitutes_component():
    cfg = apply_variant(load_config(BLG), "sucrose")
    assert [b.component for b in cfg.bom] == ["BLG-FERM", "SUCROSE"]
    with pytest.raises(ConfigError):
        apply_variant(cfg, "nope")
