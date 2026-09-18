import pytest

from ppsim.bom import BomError, explode, low_level_codes, reachable, total_requirements
from ppsim.config import BomLine


def L(p, c, q):
    return BomLine(p, c, q, str(q))


# Bike: X <- 2 A + 1 C; A <- 3 C  (C appears at levels 1 and 2 -> LLC 2)
BIKE = [L("X", "A", 2), L("X", "C", 1), L("A", "C", 3)]


def test_low_level_codes_use_deepest_level():
    assert low_level_codes(["X", "A", "C"], BIKE) == {"X": 0, "A": 1, "C": 2}


def test_cycle_detected():
    with pytest.raises(BomError, match="cycle"):
        low_level_codes(["A", "B"], [L("A", "B", 1), L("B", "A", 1)])


def test_explosion_and_summed_requirements():
    df = explode("X", BIKE, quantity=10)
    assert len(df) == 3
    assert total_requirements("X", BIKE, 10) == {"A": 20, "C": 10 + 60}


def test_reachable_orders_by_level_and_skips_unused():
    bom = BIKE + [L("Y", "Z", 1)]
    assert reachable("X", bom) == ["X", "A", "C"]
