"""Minimal Odoo JSON-2 API client (Odoo 19+). Standard library only.

    POST {ODOO_URL}/json/2/<model>/<method>
    Authorization: bearer <API key>      (key read from .odoo-apikey, gitignored)
    X-Odoo-Database: <ODOO_DB_NAME>

XML-RPC / JSON-RPC are deprecated in Odoo 19 (removal planned for Odoo 22), so this
project uses JSON-2 only. See knowledge/notes/odoo-19-community-scope.md.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

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


class Odoo:
    def __init__(self, url: Optional[str] = None, db: Optional[str] = None, key: Optional[str] = None):
        env = {**_dotenv(ROOT / ".env"), **os.environ}
        self.url = (url or env.get("ODOO_URL", "http://127.0.0.1:8069")).rstrip("/")
        self.db = db or env.get("ODOO_DB_NAME", "pps_demo")
        key_file = ROOT / ".odoo-apikey"
        self.key = key or (key_file.read_text().strip() if key_file.exists() else "")
        if not self.key:
            raise OdooError("no API key: run `make odoo-init` first")

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

    def ref(self, xmlid: str) -> int:
        module, name = xmlid.split(".", 1)
        rows = self.search_read("ir.model.data", [["module", "=", module], ["name", "=", name]], ["res_id"])
        if not rows:
            raise OdooError(f"xml id {xmlid} not found")
        return rows[0]["res_id"]
