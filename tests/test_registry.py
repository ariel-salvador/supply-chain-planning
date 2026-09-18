import pytest

from ppsim.registry import COLUMNS, RegistryError, load_registry
from conftest import REGISTRY

HEADER = ",".join(COLUMNS) + "\n"


def write(tmp_path, *rows):
    p = tmp_path / "a.csv"
    p.write_text(HEADER + "".join(r + "\n" for r in rows))
    return p


def test_repo_registry_is_valid():
    reg = load_registry(REGISTRY)
    assert reg and all(a.status in ("cited", "estimate", "mock") for a in reg.values())


def test_good_rows(tmp_path):
    reg = load_registry(write(
        tmp_path,
        "a,A,1.5,kg,1,2,Paper §1,https://x,2026-01-01,med,cited,p1;p2",
        "b,B,3,kg,,,mock planning assumption,,,low,mock,p1",
    ))
    assert reg["a"].used_in == ("p1", "p2") and reg["a"].low == 1
    assert reg["b"].status == "mock"


@pytest.mark.parametrize(
    "row, msg",
    [
        ("a,A,1,kg,,,Paper,https://x,2026-01-01,med,,p", "status"),
        ("a,A,1,kg,,,Paper,https://x,,med,cited,p", "retrieved"),
        ("a,A,1,kg,,,Paper,,2026-01-01,med,cited,p", "url"),
        ("a,A,1,kg,,,guess,,,low,mock,p", "mock"),
        ("a,A,1,kg,,,Paper,https://x,2026-01-01,sure,cited,p", "confidence"),
        ("a,A,,kg,,,Paper,https://x,2026-01-01,med,cited,p", "missing value"),
    ],
)
def test_bad_rows(tmp_path, row, msg):
    with pytest.raises(RegistryError, match=msg):
        load_registry(write(tmp_path, row))


def test_duplicate_id(tmp_path):
    r = "a,A,1,kg,,,Paper,https://x,2026-01-01,med,cited,p"
    with pytest.raises(RegistryError, match="duplicate"):
        load_registry(write(tmp_path, r, r))
