# 0009: Why Odoo Community, and what stays in Python

- **Status:** accepted (2026-09-18)
- **Context:** The portfolio should show hands-on ERP transactions (products, BOMs,
  vendors, reorder rules, MOs, POs, replenishment runs) next to the planning logic in
  code. The ERP has to be free, self-hostable and scriptable.
- **Verified limits (2026-09-18):** Module folders in the public Odoo Community 19.0
  source (github.com/odoo/odoo, branch 19.0, `addons/`):
  - **Present:** `stock`, `mrp`, `purchase`, `purchase_stock`, `sale_management`,
    `maintenance`.
  - **Absent (Enterprise-only):** `mrp_mps` (Master Production Schedule), `mrp_workorder`
    (shop floor), `mrp_plm`, `quality`, `quality_control`, `quality_mrp`, `web_gantt`
    (Gantt views), `planning`.
  - Community keeps basic MO work-order scheduling (`button_plan`) and reorder rules.

  Odoo's marketing comparison page gave contradictory summaries, so the source code was
  treated as authoritative. Details: `knowledge/notes/odoo-19-community-scope.md`.
- **Decision:** Use Odoo 19.0 Community (pinned image `odoo:19.0-20260908`, local Docker,
  localhost only) for the transaction flow: BOM → reorder rules → replenishment →
  MO/RFQ. Keep **S&OP, MPS, time fences/ATP and capacity** in the Python engine.
  Integrate through the **JSON-2** API; XML-RPC/JSON-RPC are deprecated in 19 and
  scheduled for removal in Odoo 22. Seed everything from `products/<id>.yaml`, so there
  is no manual data entry.
- **Alternatives:** Odoo Enterprise (has MPS and Gantt, but it's paid and can't be
  shown freely); ERPNext (open source with MRP, but a different ecosystem and less
  common in food and biotech job postings); a mock ERP in Python (shows no real ERP
  skills).
- **Consequences:**
  - Odoo's plan comes from reorder rules, not time-phased MRP. One scheduler run
    replenishes every shortfall in the look-ahead window *now*, while the engine
    releases each order in the week it's needed. `docs/odoo/comparison.md` quantifies
    this.
  - Demand enters Odoo as confirmed sales orders, because Community has no forecast
    or MPS.
  - The Odoo demo database, filestore and API key are local only and never committed.
