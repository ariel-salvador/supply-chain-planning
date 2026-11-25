"""Minimal Odoo JSON-2 API client (Odoo 19+). Standard library only.

    POST {ODOO_URL}/json/2/<model>/<method>
    Authorization: bearer <API key>      (key read from .odoo-apikey, gitignored)
    X-Odoo-Database: <ODOO_DB_NAME>

XML-RPC / JSON-RPC are deprecated in Odoo 19 (removal planned for Odoo 22), so this
project uses JSON-2 only. See knowledge/notes/odoo-19-community-scope.md.

Two databases (ADR 0017): ``Odoo()`` talks to the disposable demo (``pps_demo``, admin
key in ``.odoo-apikey``); ``Odoo.live()`` talks to the user's system of record
(``pps_live``) as the ``pps-bot`` user (key in ``.odoo-apikey-live``). Writes to the
live database go through :meth:`Odoo.ensure`, which is append-only.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]


def _dotenv(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


class OdooError(RuntimeError):
    pass


# Field holding the stable key of every record a script creates (ADR 0017). Created by
# odoo/bootstrap_live.py on each model the scripts write to; never copied on duplicate.
PPS_KEY = "x_pps_key"


def pending_changes(current: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, tuple]:
    """Fields whose current value differs from the desired one: {field: (current, desired)}.

    Many2one values come back from Odoo as ``[id, display_name]``; they compare by id.
    Used to *show* a diff before any master-data sync. Nothing is applied here.
    """
    out = {}
    for f, want in desired.items():
        have = current.get(f)
        if isinstance(have, list) and len(have) == 2 and isinstance(have[0], int):
            have = have[0]
        if isinstance(have, float) and isinstance(want, (int, float)):
            if abs(have - float(want)) <= 1e-9:
                continue
        elif have == want:
            continue
        out[f] = (have, want)
    return out


class Odoo:
    def __init__(
        self,
        url: Optional[str] = None,
        db: Optional[str] = None,
        key: Optional[str] = None,
        key_file: str = ".odoo-apikey",
        refs_file: Optional[str] = None,
    ):
        env = {**_dotenv(ROOT / ".env"), **os.environ}
        self.url = (url or env.get("ODOO_URL", "http://127.0.0.1:8069")).rstrip("/")
        self.db = db or env.get("ODOO_DB_NAME", "pps_demo")
        kf = ROOT / key_file
        self.key = key or (kf.read_text().strip() if kf.exists() else "")
        if not self.key:
            raise OdooError(f"no API key in {key_file}: run the matching init target first")
        # xml ids resolved by the admin bootstrap (the bot can't read ir.model.data)
        rf = ROOT / refs_file if refs_file else None
        self.refs: Dict[str, int] = json.loads(rf.read_text()) if rf and rf.exists() else {}

    @classmethod
    def live(cls, **kw: Any) -> "Odoo":
        """The user's system of record, as the pps-bot user (ADR 0017)."""
        env = {**_dotenv(ROOT / ".env"), **os.environ}
        kw.setdefault("db", env.get("ODOO_LIVE_DB_NAME", "pps_live"))
        kw.setdefault("key_file", ".odoo-apikey-live")
        kw.setdefault("refs_file", ".odoo-live-refs.json")
        return cls(**kw)

    def call(self, model: str, method: str, ids: Sequence[int] = (), **params: Any) -> Any:
        body: Dict[str, Any] = dict(params)
        if ids:
            body["ids"] = list(ids)
        req = urllib.request.Request(
            f"{self.url}/json/2/{model}/{method}",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"bearer {self.key}",
                "X-Odoo-Database": self.db,
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "ppsim-odoo-demo",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read()).get("message", "")
            except Exception:
                msg = ""
            raise OdooError(f"{model}.{method} -> HTTP {e.code}: {msg}") from None

    # convenience wrappers ---------------------------------------------------
    def search_read(self, model: str, domain: list, fields: List[str], **kw: Any) -> List[dict]:
        return self.call(model, "search_read", domain=domain, fields=fields, **kw)

    def create(self, model: str, vals: dict) -> int:
        return self.call(model, "create", vals_list=[vals])[0]

    def write(self, model: str, ids: Sequence[int], vals: dict) -> Any:
        return self.call(model, "write", ids=ids, vals=vals)

    def ensure(self, model: str, key: str, vals: dict) -> Tuple[int, bool]:
        """Append-only create: return (id, created).

        Looks the record up by its stable ``x_pps_key``. If it exists it is returned
        untouched (never written): a rerun skips what is already there, and a record the
        user has since edited in the UI is left exactly as they left it. If it does not
        exist it is created with the key. Two records with one key is an error.
        """
        if not key:
            raise OdooError("ensure() needs a non-empty key")
        found = self.search_read(model, [[PPS_KEY, "=", key]], ["id"], limit=2)
        if len(found) > 1:
            raise OdooError(f"{model}: {len(found)} records share {PPS_KEY}={key!r}")
        if found:
            return found[0]["id"], False
        return self.create(model, {**vals, PPS_KEY: key}), True

    def ref(self, xmlid: str) -> int:
        if xmlid in self.refs:
            return self.refs[xmlid]
        module, name = xmlid.split(".", 1)
        rows = self.search_read("ir.model.data", [["module", "=", module], ["name", "=", name]], ["res_id"])
        if not rows:
            raise OdooError(f"xml id {xmlid} not found")
        return rows[0]["res_id"]
