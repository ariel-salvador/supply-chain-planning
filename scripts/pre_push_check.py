"""Pre-push safety check for a repo that will be public.

1. tests (pytest)
2. assumptions registry + product configs: uncited / unlabeled values
3. files and commit messages about to be pushed: email, phone and API-key patterns
4. private deny-list ($PPS_DENYLIST, default ~/.config/pps/denylist.txt), which lives
   outside the repo. Hits are reported only as "N deny-list hits in <file>:<line>".
   Its contents are never printed, copied or logged.

    .venv/bin/python scripts/pre_push_check.py          # what would be pushed
    .venv/bin/python scripts/pre_push_check.py --all    # every tracked file
Exit code 0 = clean, 1 = findings, 2 = could not run.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_ALLOWED = re.compile(r"(@users\.noreply\.github\.com|^noreply@anthropic\.com|@example\.(com|org))$", re.I)
PHONE = re.compile(r"(?<![\w/.\-])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\w)")
API_KEYS = [
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("anthropic/openai key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}")),
    ("github token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("fred api key", re.compile(r"api_key=[0-9a-f]{32}\b", re.I)),
    ("generic secret", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]")),
]
DEFAULT_DENYLIST = "~/.config/pps/denylist.txt"
# Commit identities allowed in pushed history: GitHub noreply addresses only.
IDENTITY_ALLOWED = re.compile(r"(@users\.noreply\.github\.com|^noreply@github\.com)$", re.I)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def push_base() -> Optional[str]:
    for ref in ("@{upstream}", "origin/main"):
        try:
            return git("rev-parse", "--verify", "--quiet", ref).strip() or None
        except subprocess.CalledProcessError:
            continue
    return None


def files_to_scan(all_files: bool) -> List[str]:
    tracked = set(git("ls-files").split("\n")) - {""}
    if all_files:
        return sorted(tracked)
    base = push_base()
    changed = set(git("diff", "--name-only", "--cached").split("\n"))
    if base:
        changed |= set(git("diff", "--name-only", f"{base}...HEAD").split("\n"))
    else:
        changed |= tracked
    return sorted((changed - {""}) & tracked)


def commit_messages(all_files: bool) -> List[Tuple[str, str]]:
    base = push_base()
    rng = ["HEAD"] if (all_files or not base) else [f"{base}..HEAD"]
    out = git("log", "--format=%h%x00%B%x01", *rng)
    msgs = []
    for chunk in out.split("\x01"):
        if "\x00" in chunk:
            h, body = chunk.split("\x00", 1)
            msgs.append((f"commit {h.strip()}", body))
    return msgs


def commit_identities(all_files: bool) -> List[Tuple[str, str, str]]:
    """(commit, role, email) for every author/committer in the commits being checked."""
    base = push_base()
    rng = ["--all"] if (all_files or not base) else [f"{base}..HEAD"]
    out = git("log", "--format=%h%x00%ae%x00%ce", *rng)
    rows = []
    for line in out.splitlines():
        if line.count("\x00") == 2:
            h, ae, ce = line.split("\x00")
            rows += [(h, "author", ae), (h, "committer", ce)]
    return rows


def scan_identities(rows: Sequence[Tuple[str, str, str]]) -> List[str]:
    """Flag commit identities that aren't GitHub noreply addresses (masked)."""
    return [f"{role} email on commit {h} is not a GitHub noreply address ({mask(e)})"
            for h, role, e in rows if not IDENTITY_ALLOWED.search(e)]


def read_index(path: str) -> Optional[str]:
    """Content as it would be pushed (index = HEAD + staged)."""
    try:
        raw = subprocess.run(["git", "show", f":{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None
    if b"\x00" in raw[:8000]:
        return None  # binary
    return raw.decode("utf-8", errors="replace")


def mask(s: str) -> str:
    return s[:2] + "***" + s[-2:] if len(s) > 6 else "***"


def scan_text(name: str, text: str) -> List[str]:
    """Email / phone / API-key findings as 'kind in name:line (masked)'."""
    found = []
    for n, line in enumerate(text.splitlines(), start=1):
        for m in EMAIL.finditer(line):
            if not EMAIL_ALLOWED.search(m.group(0)):
                found.append(f"email in {name}:{n} ({mask(m.group(0))})")
        for m in PHONE.finditer(line):
            found.append(f"phone-like number in {name}:{n} ({mask(m.group(0))})")
        for kind, rx in API_KEYS:
            if rx.search(line):
                found.append(f"{kind} pattern in {name}:{n}")
    return found


def load_denylist(path: Path) -> List[str]:
    terms = []
    for line in path.read_text(errors="replace").splitlines():
        t = line.strip()
        if t and not t.startswith("#"):
            terms.append(t.lower())
    return terms


def scan_denylist(name: str, text: str, terms: Sequence[str]) -> List[str]:
    """Only counts and locations. Never include the matched term."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        hits = sum(low.count(t) for t in terms)
        if hits:
            out.append(f"{hits} deny-list hit{'s' if hits > 1 else ''} in {name}:{n}")
    return out


def check_assumptions() -> Tuple[List[str], List[str]]:
    """(errors, warnings) for the registry and every product config."""
    from ppsim.config import ConfigError, load_config
    from ppsim.registry import RegistryError, load_registry

    errors: List[str] = []
    warnings: List[str] = []
    reg_path = ROOT / "knowledge" / "assumptions.csv"
    try:
        reg = load_registry(reg_path)
    except RegistryError as e:
        return [str(e)], warnings
    used_by = {k: set() for k in reg}
    for p in sorted((ROOT / "products").glob("*.yaml")):
        try:
            cfg = load_config(p)
        except (ConfigError, RegistryError) as e:
            errors.append(f"{p.relative_to(ROOT)}: {e}")
            continue
        for a in cfg.assumptions:
            used_by[a].add(cfg.id)
    unused = []
    for k, a in reg.items():
        stale = set(a.used_in) - used_by[k]
        if stale:
            warnings.append(f"assumptions.csv: {k} lists used_in {sorted(stale)} but those products don't use it")
        if not a.used_in:
            unused.append(k)
        if a.status == "estimate" and a.confidence == "high":
            warnings.append(f"assumptions.csv: {k} is an estimate marked high confidence")
    if unused:
        warnings.append(f"assumptions.csv: {len(unused)} rows not used by any product yet (reference data): {', '.join(unused)}")
    return errors, warnings


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="pre-push safety check")
    ap.add_argument("--all", action="store_true", help="scan every tracked file, not just what would be pushed")
    ap.add_argument("--no-tests", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    failures: List[str] = []
    notes: List[str] = []

    # 1. tests
    if not args.no_tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts="], cwd=ROOT, capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        (notes if r.returncode == 0 else failures).append(f"tests: {last}")

    # 2. assumptions
    errs, warns = check_assumptions()
    failures += errs
    notes += warns
    if not errs:
        notes.append("assumptions: registry and product configs valid (all numbers cited or labeled mock/estimate)")

    # 3 + 4. content scans
    try:
        files = files_to_scan(args.all)
        msgs = commit_messages(args.all)
    except subprocess.CalledProcessError as e:
        print(f"git failed: {e}", file=sys.stderr)
        return 2

    deny_path = Path(os.path.expanduser(os.environ.get("PPS_DENYLIST", DEFAULT_DENYLIST)))
    terms: List[str] = []
    if deny_path.is_file():
        terms = load_denylist(deny_path)
        notes.append(f"deny-list: loaded ({len(terms)} entries)")
    else:
        notes.append("WARNING: deny-list not found at $PPS_DENYLIST / default path; skipped that scan")

    for name in files:
        text = read_index(name)
        if text is None:
            continue
        failures += scan_text(name, text)
        if terms:
            failures += scan_denylist(name, text, terms)
    failures += scan_identities(commit_identities(args.all))
    for name, body in msgs:
        failures += scan_text(name, body)
        if terms:
            failures += scan_denylist(name, body, terms)

    print(f"pre-push check: {len(files)} files, {len(msgs)} commit messages scanned")
    for n in notes:
        print("  ok/note:", n)
    for f in failures:
        print("  FINDING:", f)
    print("RESULT:", "clean" if not failures else f"{len(failures)} finding(s); do not push until resolved")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
