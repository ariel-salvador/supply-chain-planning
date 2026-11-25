"""Guarded Odoo database operations (ADR 0017).

    .venv/bin/python scripts/odoo_admin.py exists  <db>
    .venv/bin/python scripts/odoo_admin.py drop    <db> [--if-exists]
    .venv/bin/python scripts/odoo_admin.py backup  <db> [--out backups]
    .venv/bin/python scripts/odoo_admin.py restore-test <db>
    .venv/bin/python scripts/odoo_admin.py init-live
    .venv/bin/python scripts/odoo_admin.py bootstrap-live
    .venv/bin/python scripts/odoo_admin.py nuke --i-understand-this-deletes-pps-live

Two databases live in one Odoo instance: ``pps_demo`` is disposable (``make odoo-demo``
rebuilds it), ``pps_live`` is the user's system of record. The rules enforced here:

- ``drop`` refuses the live database, whatever flags are passed;
- ``init-live`` only creates the live database when it does not exist yet;
- ``nuke`` (delete every volume) refuses unless a backup of the live database younger
  than ``FRESH_BACKUP_HOURS`` exists and verifies;
- backups are Odoo's own zip format (database dump + filestore, restorable with
  ``odoo db load``), written to ``backups/`` (gitignored) and verified after writing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from odoo_client import _dotenv  # noqa: E402

XBIN = Path("/Applications/OrbStack.app/Contents/MacOS/xbin")
APPS = "stock,mrp,purchase,sale_management"
FRESH_BACKUP_HOURS = 24
DB_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class AdminError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# pure rules (unit-tested)
# ---------------------------------------------------------------------------


def settings(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    e = {**_dotenv(ROOT / ".env"), **os.environ} if env is None else dict(env)
    e.setdefault("ODOO_DB_NAME", "pps_demo")
    e.setdefault("ODOO_LIVE_DB_NAME", "pps_live")
    return e


def protected(env: Dict[str, str]) -> set:
    return {env["ODOO_LIVE_DB_NAME"]}


def check_droppable(db: str, protected_dbs: set) -> None:
    if not DB_NAME.match(db):
        raise AdminError(f"refusing: {db!r} is not a plain database name")
    if db in protected_dbs:
        raise AdminError(f"refusing to drop {db!r}: it is the live system of record (ADR 0017)")


def backup_path(db: str, now: dt.datetime, outdir: Path) -> Path:
    return outdir / f"{db}-{now.strftime('%Y%m%dT%H%M%SZ')}.zip"


def verify_backup(path: Path, require_filestore: bool = True) -> Dict[str, int]:
    """An Odoo zip backup must contain dump.sql, manifest.json and a filestore.

    Every Odoo database has filestore files (asset bundles at least), so an empty
    filestore means the dump couldn't find it: treat that as a failed backup.
    """
    if not path.exists() or path.stat().st_size == 0:
        raise AdminError(f"backup {path} is missing or empty")
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            bad = z.testzip()
    except zipfile.BadZipFile as e:
        raise AdminError(f"backup {path} is not a valid zip: {e}") from None
    if bad:
        raise AdminError(f"backup {path} has a corrupt member: {bad}")
    missing = {"dump.sql", "manifest.json"} - set(names)
    if missing:
        raise AdminError(f"backup {path} lacks {sorted(missing)}")
    filestore = sum(n.startswith("filestore/") and not n.endswith("/") for n in names)
    if require_filestore and filestore == 0:
        raise AdminError(f"backup {path} has no filestore (attachments): incomplete backup")
    return {"bytes": path.stat().st_size, "entries": len(names), "filestore_files": filestore}


def latest_backup(db: str, outdir: Path) -> Optional[Path]:
    found = sorted(outdir.glob(f"{db}-*.zip"))
    return found[-1] if found else None


def has_fresh_backup(db: str, outdir: Path, now: dt.datetime, max_age_h: float = FRESH_BACKUP_HOURS) -> bool:
    p = latest_backup(db, outdir)
    if p is None:
        return False
    m = re.search(r"-(\d{8}T\d{6}Z)\.zip$", p.name)
    if not m:
        return False
    taken = dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    if now - taken > dt.timedelta(hours=max_age_h):
        return False
    verify_backup(p)
    return True


# ---------------------------------------------------------------------------
# docker plumbing
# ---------------------------------------------------------------------------


def compose(env: Dict[str, str]) -> List[str]:
    if shutil.which("docker") and subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
        return ["docker", "compose"]
    os.environ.setdefault("DOCKER_HOST", f"unix://{Path.home()}/.orbstack/run/docker.sock")
    return [str(XBIN / "docker-compose")]


def _run(cmd: Sequence[str], env: Dict[str, str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=ROOT, env={**os.environ, **env}, **kw)


def db_exists(db: str, env: Dict[str, str]) -> bool:
    out = _run(compose(env) + ["exec", "-T", "db", "psql", "-U", env["ODOO_DB_USER"], "-d", "postgres",
                               "-tAc", f"select 1 from pg_database where datname = '{db}'"],
               env, capture_output=True, text=True)
    if out.returncode != 0:
        raise AdminError("could not query Postgres; is the stack up? (`make odoo-up`)")
    return out.stdout.strip() == "1"


def db_cli_args(args: Sequence[str], conf_path: str) -> List[str]:
    """Place `-c <conf>` right after `db`: the `odoo db` parser only accepts connection
    options there (the image's entrypoint appends them at the end, which it rejects)."""
    args = list(args)
    if not args or args[0] != "db":
        raise AdminError("odoo_cli() is for `odoo db ...` commands only")
    return ["db", "-c", conf_path, *args[1:]]


def odoo_cli(args: Sequence[str], env: Dict[str, str], mounts: Sequence[str] = (), **kw) -> subprocess.CompletedProcess:
    """`odoo db ...` with the connection in a short-lived config file.

    The file lives in a private, gitignored directory (0700/0600), is mounted read-only
    into the one-off container and deleted afterwards, so the database password never
    appears on a command line or in a process listing.
    """
    run_dir = ROOT / ".odoo-run"
    run_dir.mkdir(mode=0o700, exist_ok=True)
    fd, conf = tempfile.mkstemp(dir=run_dir, suffix=".conf")
    try:
        with os.fdopen(fd, "w") as f:
            # data_dir must match the image's own config, or dumps silently skip the
            # filestore (attachments) and restores write it where the server never looks
            f.write("[options]\ndb_host = db\ndb_port = 5432\ndata_dir = /var/lib/odoo\n"
                    f"db_user = {env['ODOO_DB_USER']}\ndb_password = {env['ODOO_DB_PASSWORD']}\n")
        os.chmod(conf, 0o600)
        vols = ["-v", f"{conf}:/run/pps-odoo.conf:ro"]
        for m in mounts:
            vols += ["-v", m]
        return _run(compose(env) + ["run", "--rm", "-T", "--entrypoint", "odoo", *vols, "odoo",
                                    *db_cli_args(args, "/run/pps-odoo.conf")], env, **kw)
    finally:
        os.unlink(conf)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def cmd_backup(db: str, env: Dict[str, str], outdir: Path) -> Path:
    if not db_exists(db, env):
        raise AdminError(f"database {db!r} does not exist")
    outdir.mkdir(parents=True, exist_ok=True)
    path = backup_path(db, dt.datetime.now(dt.timezone.utc), outdir)
    with path.open("wb") as f:
        r = odoo_cli(["db", "dump", db, "-"], env, stdout=f, stderr=subprocess.PIPE)
    if r.returncode != 0:
        path.unlink(missing_ok=True)
        raise AdminError(f"odoo db dump failed (exit {r.returncode})")
    path.chmod(0o600)
    info = verify_backup(path)
    print(f"backup ok: {path.relative_to(ROOT)}  {info['bytes'] / 1e6:.1f} MB, "
          f"{info['filestore_files']} filestore files")
    return path


def cmd_restore_test(db: str, env: Dict[str, str], outdir: Path) -> None:
    """Load the latest backup of `db` into a throwaway database, check it, drop it."""
    path = latest_backup(db, outdir)
    if path is None:
        raise AdminError(f"no backup of {db} in {outdir}")
    verify_backup(path)
    scratch = f"{db}_restore_test"
    check_droppable(scratch, protected(env))
    if db_exists(scratch, env):
        cmd_drop(scratch, env, if_exists=True)
    r = odoo_cli(["db", "load", scratch, f"/backups/{path.name}"], env,
                 mounts=[f"{outdir.resolve()}:/backups:ro"], capture_output=True, text=True)
    try:
        if r.returncode != 0 or not db_exists(scratch, env):
            raise AdminError(f"restoring {path.name} failed")
        out = _run(compose(env) + ["exec", "-T", "db", "psql", "-U", env["ODOO_DB_USER"], "-d", scratch, "-tAc",
                                   "select count(*) from res_users"], env, capture_output=True, text=True)
        users = int(out.stdout.strip() or 0)
        if users < 1:
            raise AdminError(f"restored {scratch} has no users; backup is not usable")
        want = verify_backup(path)["filestore_files"]
        ls = _run(compose(env) + ["run", "--rm", "-T", "--entrypoint", "sh", "odoo", "-c",
                                  f"find /var/lib/odoo/filestore/{scratch} -type f 2>/dev/null | wc -l"],
                  env, capture_output=True, text=True)
        got = int((ls.stdout.strip().splitlines() or ["0"])[-1])
        if got != want:
            raise AdminError(f"filestore mismatch after restore: backup has {want} files, restored {got}")
        print(f"restore test ok: {path.name} -> {scratch} ({users} users, {got}/{want} filestore files), now dropped")
    finally:
        if db_exists(scratch, env):
            odoo_cli(["db", "drop", scratch], env, capture_output=True, text=True)


def cmd_rehearse(env: Dict[str, str], outdir: Path) -> None:
    """Replace the disposable demo with a copy of the latest live backup.

    A rehearsal target for anything that writes to the live database (the history
    backfill): same records, same bot and API keys, but losing it costs nothing.
    `make odoo-demo` rebuilds the normal demo afterwards.
    """
    live, demo = env["ODOO_LIVE_DB_NAME"], env.get("ODOO_DB_NAME", "pps_demo")
    path = latest_backup(live, outdir)
    if path is None:
        raise AdminError(f"no backup of {live} in {outdir}: run `make odoo-backup` first")
    verify_backup(path)
    check_droppable(demo, protected(env))
    if db_exists(demo, env):
        cmd_drop(demo, env, if_exists=True)
    r = odoo_cli(["db", "load", demo, f"/backups/{path.name}"], env,
                 mounts=[f"{outdir.resolve()}:/backups:ro"], capture_output=True, text=True)
    if r.returncode != 0 or not db_exists(demo, env):
        raise AdminError(f"loading {path.name} into {demo} failed")
    print(f"rehearsal ready: {demo} is now a copy of {path.name} (rebuild the demo later with `make odoo-demo`)")


def cmd_drop(db: str, env: Dict[str, str], if_exists: bool) -> None:
    check_droppable(db, protected(env))
    if not db_exists(db, env):
        if if_exists:
            print(f"{db}: not present, nothing to drop")
            return
        raise AdminError(f"database {db!r} does not exist")
    r = odoo_cli(["db", "drop", db], env, capture_output=True, text=True)
    if r.returncode != 0:
        raise AdminError(f"odoo db drop {db} failed: {r.stderr.strip()[-300:]}")
    print(f"dropped {db} (database + filestore)")


def cmd_bootstrap_live(env: Dict[str, str]) -> None:
    live = env["ODOO_LIVE_DB_NAME"]
    if not db_exists(live, env):
        raise AdminError(f"{live} does not exist: run `make odoo-live-init`")
    company, horizon_days = _config_settings()
    script = (ROOT / "odoo" / "bootstrap_live.py").read_text()
    r = _run(compose(env) + ["run", "--rm", "-T", "-e", "ODOO_ADMIN_PASSWORD", "-e", "PPS_COMPANY_NAME",
                             "-e", "PPS_HORIZON_DAYS", "odoo", "odoo", "shell", "-d", live, "--no-http"],
             {**env, "PPS_COMPANY_NAME": company, "PPS_HORIZON_DAYS": str(horizon_days)},
             input=script, capture_output=True, text=True)
    key = re.search(r"^PPS_BOT_API_KEY=(\S+)$", r.stdout, re.M)
    reader = re.search(r"^PPS_READER_API_KEY=(\S+)$", r.stdout, re.M)
    refs = re.search(r"^PPS_REFS=(\{.*\})$", r.stdout, re.M)
    if r.returncode != 0 or not key or not reader or not refs:
        raise AdminError("bootstrap_live.py failed (see `make odoo-logs`); no key written")
    for name, value in ((".odoo-apikey-live", key.group(1)), (".odoo-apikey-reader", reader.group(1)),
                        (".odoo-live-refs.json", refs.group(1))):
        p = ROOT / name
        p.write_text(value + "\n")
        p.chmod(0o600)
    # The running server caches each user's groups; changes made from this separate
    # shell process aren't seen until it restarts (a new bot group stays "denied").
    _run(compose(env) + ["restart", "odoo"], env, capture_output=True)
    wait_for_odoo(env)
    print(f"{live}: bootstrap ok (keys -> .odoo-apikey-live, .odoo-apikey-reader; refs -> .odoo-live-refs.json); odoo restarted")


def wait_for_odoo(env: Dict[str, str], tries: int = 60) -> None:
    import time
    import urllib.request

    url = env.get("ODOO_URL", "http://127.0.0.1:8069").rstrip("/") + "/web/login"
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except Exception:
            time.sleep(2)
    raise AdminError("odoo did not come back after restart")


def cmd_init_live(env: Dict[str, str]) -> None:
    live = env["ODOO_LIVE_DB_NAME"]
    if db_exists(live, env):
        raise AdminError(f"{live} already exists; nothing created. "
                         "To refresh the bot key, run `make odoo-live-bootstrap`.")
    r = _run(compose(env) + ["run", "--rm", "odoo", "odoo", "-d", live, "-i", APPS,
                             "--stop-after-init", "--no-http"], env, capture_output=True, text=True)
    if r.returncode != 0 or not db_exists(live, env):
        raise AdminError(f"creating {live} failed: {r.stderr.strip()[-300:]}")
    print(f"created {live} with {APPS}")
    cmd_bootstrap_live(env)


def cmd_nuke(env: Dict[str, str], outdir: Path) -> None:
    live = env["ODOO_LIVE_DB_NAME"]
    now = dt.datetime.now(dt.timezone.utc)
    if db_exists(live, env) and not has_fresh_backup(live, outdir, now):
        raise AdminError(f"refusing: no verified backup of {live} from the last "
                         f"{FRESH_BACKUP_HOURS} h. Run `make odoo-backup` first.")
    r = _run(compose(env) + ["down", "-v"], env)
    if r.returncode != 0:
        raise AdminError("docker compose down -v failed")
    print("all Odoo volumes deleted. Restore pps_live with "
          "`odoo db load` from the latest zip in backups/.")


def _config_settings() -> tuple:
    """(fictional company name, replenishment horizon in days) from the product config."""
    sys.path.insert(0, str(ROOT / "src"))
    from ppsim.config import load_config  # noqa: E402
    from ppsim.registry import load_registry  # noqa: E402

    cfg = load_config(ROOT / "products" / "blg_whey_protein.yaml")
    days_per_week = load_registry(ROOT / "knowledge" / "assumptions.csv")["days_per_week"].value
    name = cfg.company.name if cfg.company else "Demo company (fictional)"
    return name, cfg.horizon * days_per_week


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("exists").add_argument("db")
    d = sub.add_parser("drop")
    d.add_argument("db")
    d.add_argument("--if-exists", action="store_true")
    b = sub.add_parser("backup")
    b.add_argument("db")
    b.add_argument("--out", type=Path, default=ROOT / "backups")
    rt = sub.add_parser("restore-test")
    rt.add_argument("db")
    rt.add_argument("--out", type=Path, default=ROOT / "backups")
    rh = sub.add_parser("rehearse", help="copy the latest pps_live backup into pps_demo")
    rh.add_argument("--out", type=Path, default=ROOT / "backups")
    sub.add_parser("init-live")
    sub.add_parser("bootstrap-live")
    n = sub.add_parser("nuke")
    n.add_argument("--i-understand-this-deletes-pps-live", dest="confirm", action="store_true")
    n.add_argument("--out", type=Path, default=ROOT / "backups")
    args = ap.parse_args(argv)
    env = settings()
    try:
        if args.cmd == "exists":
            return 0 if db_exists(args.db, env) else 1
        if args.cmd == "drop":
            cmd_drop(args.db, env, args.if_exists)
        elif args.cmd == "backup":
            cmd_backup(args.db, env, args.out)
        elif args.cmd == "restore-test":
            cmd_restore_test(args.db, env, args.out)
        elif args.cmd == "rehearse":
            cmd_rehearse(env, args.out)
        elif args.cmd == "init-live":
            cmd_init_live(env)
        elif args.cmd == "bootstrap-live":
            cmd_bootstrap_live(env)
        elif args.cmd == "nuke":
            if not args.confirm:
                raise AdminError("refusing: pass --i-understand-this-deletes-pps-live")
            cmd_nuke(env, args.out)
    except AdminError as e:
        print(f"odoo_admin: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
