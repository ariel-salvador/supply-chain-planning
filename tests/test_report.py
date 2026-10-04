import importlib.util
import json
import re

import pandas as pd
import pytest

from ppsim import fred
from conftest import BLG, ROOT

spec = importlib.util.spec_from_file_location("build_report", ROOT / "reports" / "build_report.py")
br = importlib.util.module_from_spec(spec)
spec.loader.exec_module(br)


@pytest.fixture
def fake_prices(monkeypatch):
    idx = pd.date_range("2016-01-01", periods=24, freq="MS")
    data = {"PMAIZMTUSDM": pd.Series(200.0, index=idx), "PSUGAISAUSDM": pd.Series(15.0, index=idx)}
    monkeypatch.setattr(fred, "fetch_series", lambda sid, **k: data[sid])
    monkeypatch.setattr(fred, "cache_metadata", lambda sid, *a: {"series": sid})


def test_report_builds_self_contained_html(tmp_path, fake_prices):
    out = tmp_path / "r.html"
    assert br.main([str(BLG), "--out", str(out)]) == 0
    html = out.read_text()
    data = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    titles = [c["title"] for row in data["rows"] for c in row]
    assert len(titles) == 13 and any("Rough-cut" in t for t in titles)
    # the sourcing section (M6) renders, and no real supplier name can appear
    assert any(t.startswith("RFQ scorecard") for t in titles)
    assert any(t.startswith("Should-cost vs quotes") for t in titles)
    assert any(t.startswith("Total cost of ownership") for t in titles)
    assert any("MOCK" in b[0] or "MOCK" in b[1] for b in data["banner"])
    assert "Demand is MOCK." in [b[0] for b in data["banner"]]
    assert "International Monetary Fund" in data["footer"]
    # no external scripts: page works offline
    assert "<script src" not in html
