import os
import time

import pytest

from ppsim import fred
from conftest import ROOT

SAMPLE = (ROOT / "tests" / "fixtures" / "fred_sample.csv").read_text()


def test_parse_drops_missing_dot_values():
    s = fred.parse_csv(SAMPLE, "PTEST")
    assert s.tolist() == [100.0, 110.5]
    assert str(s.index[0].date()) == "2024-01-01"


def test_parse_rejects_wrong_header():
    with pytest.raises(fred.FredError):
        fred.parse_csv(SAMPLE, "OTHER")


def test_offline_uses_stale_cache_and_never_downloads(tmp_path, monkeypatch):
    (tmp_path / "PTEST.csv").write_text(SAMPLE)
    old = time.time() - 30 * 86400
    os.utime(tmp_path / "PTEST.csv", (old, old))
    monkeypatch.setattr(fred, "_download", lambda *a, **k: pytest.fail("should not download"))
    assert len(fred.fetch_series("PTEST", cache_dir=tmp_path, offline=True)) == 2


def test_offline_without_cache_errors(tmp_path):
    with pytest.raises(fred.FredError, match="offline"):
        fred.fetch_series("PTEST", cache_dir=tmp_path, offline=True)


def test_stale_cache_refreshes(tmp_path, monkeypatch):
    (tmp_path / "PTEST.csv").write_text("observation_date,PTEST\n2020-01-01,1\n")
    old = time.time() - 30 * 86400
    os.utime(tmp_path / "PTEST.csv", (old, old))
    monkeypatch.setattr(fred, "_download", lambda *a, **k: SAMPLE)
    assert len(fred.fetch_series("PTEST", cache_dir=tmp_path)) == 2
    assert fred.cache_metadata("PTEST", tmp_path)["n"] == 2
