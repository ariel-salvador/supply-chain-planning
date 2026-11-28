"""Publish the built Evidence dashboard to the repo's ``gh-pages`` branch (GitHub Pages).

    make evidence-publish             # extract -> build -> scan -> push
    .venv/bin/python scripts/publish_evidence.py --dry-run   # list what would go public

The site is static (HTML, JS, and the query results as data files); the data comes from
the local ERP, which GitHub can't reach, so it is built here and the output pushed.
Before anything leaves the machine, every text file in the build is scanned like a git
push (emails, phone numbers, API keys, the private deny-list); any finding stops it.
``gh-pages`` holds only the build, force-replaced on each publish (no history to leak).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "dashboard" / "evidence" / "build"
sys.path.insert(0, str(ROOT / "scripts"))

import pre_push_check as ppc  # noqa: E402

VENDOR_CONTACT = "support@evidence.dev"
TEXT = {".html", ".js", ".css", ".json", ".txt", ".svg", ".xml", ".map", ".md", ".csv"}


def site_root(build: Path) -> Path:
    """The folder holding index.html (Evidence nests it under the base path)."""
    hits = sorted(build.rglob("index.html"), key=lambda p: len(p.parts))
    if not hits:
        raise SystemExit(f"no index.html under {build}: run the build first")
    return hits[0].parent


def scan(site: Path) -> List[str]:
    import os
    terms = []
    deny = Path(os.path.expanduser(os.environ.get("PPS_DENYLIST", ppc.DEFAULT_DENYLIST)))
    if deny.exists():
        terms = ppc.load_denylist(deny)
    findings = []
    for f in sorted(site.rglob("*")):
        if f.is_file() and f.suffix in TEXT:
            text = f.read_text(errors="replace")
            name = str(f.relative_to(site))
            # the framework's own menu links its vendor support address; nothing else is exempt
            findings += ppc.scan_text(name, text.replace(VENDOR_CONTACT, ""))
            findings += ppc.scan_denylist(name, text, terms)
    return findings


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def publish(site: Path) -> None:
    remote = git("remote", "get-url", "origin", cwd=ROOT)
    name, email = git("config", "user.name", cwd=ROOT), git("config", "user.email", cwd=ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "site"
        shutil.copytree(site, out)
        (out / ".nojekyll").write_text("")           # serve _app/ folders as-is
        git("init", "-q", "-b", "gh-pages", cwd=out)
        git("config", "user.name", name, cwd=out)
        git("config", "user.email", email, cwd=out)
        git("add", "-A", cwd=out)
        git("commit", "-q", "-m", "Publish dashboard (built locally from the ERP marts)", cwd=out)
        git("push", "-q", "--force", remote, "gh-pages:gh-pages", cwd=out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    site = site_root(BUILD)
    files = [f for f in site.rglob("*") if f.is_file()]
    size = sum(f.stat().st_size for f in files)
    print(f"site: {site.relative_to(ROOT)}  {len(files)} files, {size / 1e6:.1f} MB")
    data = sorted(str(f.relative_to(site)) for f in files if f.suffix in (".parquet", ".arrow", ".json")
                  and "data" in f.parts)
    for d in data:
        print(f"  data: {d}")
    findings = scan(site)
    for f in findings:
        print(f"  FINDING: {f}")
    if findings:
        print("not published: resolve the findings first")
        return 1
    if args.dry_run:
        print("dry run: scan clean, nothing pushed")
        return 0
    publish(site)
    print("pushed to gh-pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
