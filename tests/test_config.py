import copy

import pytest

from ppsim.config import ConfigError, apply_variant, evaluate, load_config, parse_config
from conftest import BLG


def test_minimal_config_parses(minimal_raw):
    cfg = parse_config(minimal_raw)
    assert cfg.derived["k2"] == 4
    assert cfg.bom[0].qty_per == 2
    assert cfg.items["B"].planning.lead_time == 1


@pytest.mark.parametrize("field", ["source", "locator", "unit"])
def test_parameter_without_citation_fields_is_rejected(minimal_raw, field):
    raw = copy.deepcopy(minimal_raw)
    del raw["parameters"]["k"][field]
    with pytest.raises(ConfigError, match=field):
        parse_config(raw)


def test_parameter_citing_undeclared_source_is_rejected(minimal_raw):
    raw = copy.deepcopy(minimal_raw)
    raw["parameters"]["k"]["source"] = "nope"
    with pytest.raises(ConfigError, match="not declared"):
        parse_config(raw)


def test_parameter_value_must_be_a_number(minimal_raw):
    raw = copy.deepcopy(minimal_raw)
    raw["parameters"]["k"]["value"] = "1 + 1"
    with pytest.raises(ConfigError, match="derived"):
        parse_config(raw)


def test_demand_must_be_explicitly_mock(minimal_raw):
    raw = copy.deepcopy(minimal_raw)
    raw["demand"]["mock"] = False
    with pytest.raises(ConfigError, match="mock"):
        parse_config(raw)


def test_fractional_lead_time_is_rejected(minimal_raw):
    raw = copy.deepcopy(minimal_raw)
    raw["items"][1]["planning"]["lead_time"] = "k / 3"
    with pytest.raises(ConfigError, match="whole number"):
        parse_config(raw)


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


def test_blg_config_every_parameter_cited():
    cfg = load_config(BLG)
    assert cfg.parameters, "case 1 should have cited parameters"
    for p in cfg.parameters.values():
        assert p.source in cfg.sources and p.locator
    assert cfg.demand.mock is True


def test_blg_derived_values():
    cfg = load_config(BLG)
    d = cfg.derived
    assert d["rblg_kg_per_kg_product"] == pytest.approx(0.858 / 0.975)
    assert d["sugar_kg_per_kg_rblg"] == pytest.approx(1 / (0.223 * 0.90))
    assert d["corn_kg_per_glucose_kg"] == pytest.approx((25 / 14) * 162.141 / 180.156)
    assert cfg.items["BLG-FERM"].planning.lead_time == 1  # 144 h cycle -> 1 week


def test_variant_substitutes_component():
    cfg = apply_variant(load_config(BLG), "sucrose")
    assert [b.component for b in cfg.bom] == ["BLG-FERM", "SUCROSE"]
    with pytest.raises(ConfigError):
        apply_variant(cfg, "nope")
