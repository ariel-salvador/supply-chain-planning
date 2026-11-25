import importlib.util

import pytest

from conftest import ROOT

spec = importlib.util.spec_from_file_location("ppc", ROOT / "scripts" / "pre_push_check.py")
ppc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppc)


# fixtures are concatenated at runtime so this file itself passes the scan
@pytest.mark.parametrize(
    "text, kind",
    [
        ("contact jane.doe" + "@corp.example.net today", "email"),
        ("call 555-123-" + "4567", "phone"),
        ("tel: (555) 123-" + "4567", "phone"),
        ("+1 555 123 " + "4567", "phone"),
        ("key = AKIA" + "ABCDEFGHIJKLMNOP", "aws"),
        ("ANTHROPIC_API_KEY='sk-" + "ant-abcdefghijklmnopqrstuvwxyz'", "anthropic"),
        ("-----BEGIN RSA " + "PRIVATE KEY-----", "private key"),
        ("fredgraph?api_key=" + "0123456789abcdef0123456789abcdef", "fred"),
    ],
)
def test_detects(text, kind):
    found = ppc.scan_text("f.txt", text)
    assert any(kind in f for f in found), found


@pytest.mark.parametrize(
    "text",
    [
        "Co-Authored-By: Claude <noreply@anthropic.com>",
        "author 123+someone@users.noreply.github.com",
        "doi 10.1007/s11367-022-02087-0 pages 1017-1034",
        "retrieved 2026-09-18, value 0.45359237",
        "see https://example.org/a",
    ],
)
def test_no_false_positives(text):
    assert ppc.scan_text("f.txt", text) == []


def test_email_is_masked():
    found = ppc.scan_text("f.txt", "reach jane.doe" + "@corp.example.net")
    assert "jane.doe" not in found[0]


def test_denylist_reports_location_only(tmp_path):
    d = tmp_path / "deny.txt"
    d.write_text("# comment\nSecretCorp\n\nproject-x\n")
    terms = ppc.load_denylist(d)
    out = ppc.scan_denylist("docs/a.md", "ok line\nwe met secretcorp about Project-X and SECRETCORP\n", terms)
    assert out == ["3 deny-list hits in docs/a.md:2"]
    assert all("secretcorp" not in o.lower() and "project-x" not in o.lower() for o in out)


def test_repo_assumptions_clean():
    errors, _ = ppc.check_assumptions()
    assert errors == []


def test_identity_scan_allows_only_github_noreply():
    rows = [
        ("abc1234", "author", "123+someone@users.noreply.github.com"),
        ("abc1234", "committer", "noreply@github.com"),
        ("def5678", "author", "jane.doe" + "@example-mail.com"),
        ("def5678", "committer", "noreply" + "@anthropic.com"),
    ]
    found = ppc.scan_identities(rows)
    assert len(found) == 2
    assert all("def5678" in f for f in found)
    assert all("jane.doe" not in f for f in found)  # masked


def test_lockfile_maintainer_emails_are_not_findings():
    line = '"deprecated": "contact ' + "maintainer" + "@" + 'example.net"'
    assert not any(f.startswith("email") for f in ppc.scan_text("web/package-lock.json", line))
    assert any(f.startswith("email") for f in ppc.scan_text("notes.md", line))
