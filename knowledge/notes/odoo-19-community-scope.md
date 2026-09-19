# Odoo 19 Community: what's in scope, and the external API

- **Sources:**
  - Odoo Community source, branch 19.0: https://github.com/odoo/odoo/tree/19.0/addons
    (module presence checked via the GitHub API)
  - Odoo 19.0 developer docs, External API:
    https://www.odoo.com/documentation/19.0/developer/reference/external_api.html
    (source: odoo/documentation, `content/developer/reference/external_api.rst`, branch 19.0)
  - Official Docker images: https://hub.docker.com/_/odoo , https://hub.docker.com/_/postgres
- **Retrieved:** 2026-09-18
- **Reliability:** primary sources (the vendor's own code and docs). The marketing pages
  (odoo.com/page/editions) gave contradictory summaries, so we relied on the code.
- **reviewed:** false

## Key facts

- **Current stable:** Odoo 19.0 (`release.py` version_info 19.0 FINAL). The newest pinned
  image is `odoo:19.0-20260908` (about 694 MB compressed, arm64).
- **Postgres:** minimum version 13 (`MIN_PG_VERSION = 13` in `odoo/service/server.py`).
  The pinned image is `postgres:17.11-bookworm` (about 154 MB compressed, arm64).
- **In Community 19.0** (module folder exists): `stock`, `mrp`, `purchase`,
  `purchase_stock`, `sale_management`, `mrp_account`, `stock_account`, `maintenance`.
- **Not in Community 19.0** (no module folder, so Enterprise-only): `mrp_mps` (Master
  Production Schedule), `mrp_workorder` (shop-floor/tablet work orders), `mrp_plm`,
  `quality`, `quality_control`, `quality_mrp`, `web_gantt` (Gantt views), `planning`.
- **Community still has:** MO work-order scheduling against work centers
  (`mrp.production.button_plan` / `_plan_workorders`), and reorder rules
  (`stock.warehouse.orderpoint`) with manual/auto trigger and `action_replenish`.
- **External API:** JSON-2 at `POST /json/2/<model>/<method>`, with headers
  `Authorization: bearer <API key>` and optional `X-Odoo-Database`. The docs' own
  traceback example runs from a `community` path, so it's available in Community. API
  keys are created in Preferences → Account Security, or programmatically with
  `res.users.apikeys.generate`, which itself needs an existing key.
- **Deprecation:** XML-RPC and JSON-RPC (`/xmlrpc`, `/xmlrpc/2`, `/jsonrpc`) are
  deprecated and scheduled for removal in **Odoo 22 (fall 2028)** (External API docs,
  "XML-RPC / JSON-RPC" section).

## Installers (measured Content-Length, 2026-09-18, Apple Silicon)
- Docker Desktop `Docker.dmg`: about 584 MB.
- OrbStack v2.2.3 dmg: about 463 MB.

## Implications
- Use JSON-2, not XML-RPC, since the latter is deprecated. Bootstrap the first API key
  with `odoo shell` inside the container, so there's no manual UI step.
- S&OP, MPS and capacity stay in the Python engine. Odoo covers BOM → reorder rules →
  replenishment → MO/PO.
