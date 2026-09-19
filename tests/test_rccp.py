import numpy as np
import pytest

from ppsim.rccp import BorLine, Resource, level, load_profile

RES = {"R": Resource("R", "reactor", units=2, hours_per_week=100, availability=0.5)}  # 100 h/week


def test_capacity_and_load_profile():
    assert RES["R"].capacity_h == 100
    df = load_profile({"X": [1, 3, 0]}, [BorLine("X", "R", 40)], RES, ["a", "b", "c"])
    assert df["load_h"].tolist() == [40, 120, 0]
    assert df["overloaded"].tolist() == [False, True, False]
    assert df["utilization"].tolist() == pytest.approx([0.4, 1.2, 0.0])


def test_level_pulls_whole_lots_to_latest_earlier_week():
    # 40 h per unit, 100 h capacity -> at most 2 units/week; lot = 1 unit
    rel, notes = level([1, 1, 4, 0], hours_per_unit=40, capacity_h=100, lot=1, max_pull=2)
    assert rel.tolist() == [2, 2, 2, 0]
    assert sum(rel) == 6 and len(notes) == 2
    assert notes[0] == "moved 1 from bucket 2 to bucket 1"


def test_level_respects_pull_limit_and_reports_residual():
    rel, notes = level([0, 0, 0, 6], 40, 100, lot=1, max_pull=1)
    assert rel.tolist() == [0, 0, 2, 4]  # week 1 is out of reach, so week 3 stays over
    assert "no earlier slot within 1" in notes[-1]
    rel, notes = level([4, 0], 40, 100, lot=1, max_pull=3)  # nothing earlier than week 0
    assert rel.tolist() == [4, 0]
    assert "no earlier slot" in notes[-1]


def test_level_counts_other_items_load():
    rel, _ = level([0, 2], 40, 100, lot=1, max_pull=1, other_load_h=[80, 0])
    assert rel.tolist() == [0, 2]  # week 0 has only 20 h spare, can't take a 40 h lot


def test_continuous_level_without_lot():
    rel, _ = level([0, 3], 40, 100, lot=0, max_pull=1)
    assert rel.tolist() == pytest.approx([0.5, 2.5])
