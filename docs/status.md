# Status (handoff)

_Last updated: 2026-11-24 · repo **`ariel-salvador/supply-chain-planning`**, **public**
since 2026-11-24. The old repo, now `production-planning-simulator-archive`, stays private
forever: its PR pages reference commits with the author's old email._

## Current state
- **Built and merged:** M1–M6 (planning engine through sourcing), the Odoo 19 Community
  demo, the static chart report. Milestone history: [`CHANGELOG.md`](../CHANGELOG.md).
- **Launched:** public since 2026-11-24 ([`public-launch-checklist.md`](public-launch-checklist.md)).
- **Dashboard Phase 0 done** (ADR 0017): `pps_live` exists as the system of record, with
  the `pps-bot` user, append-only `Odoo.live().ensure()`, verified backups, a restore
  test, and guarded operations. `make odoo-demo` now rebuilds only `pps_demo`.

## Decisions for the dashboard work (2026-11-24, delegated by the user)
1. **Two Odoo databases.** `pps_demo` stays disposable (`make odoo-demo` rebuilds it, so
   anyone can reproduce the demo). `pps_live` is the user's system of record: no script
   ever drops or resets it, and reset targets refuse to touch it.
2. **Master-data conflicts: Python asks, and does nothing by default.** When the config
   and a record the user edited in the UI disagree, a sync prints a diff and applies it
   only on explicit confirmation. Manual edits are never silently overwritten.
3. **Dashboard platform:** one data layer (Odoo extract → marts, DuckDB + CSV) feeding
   **Tableau Public** (flagship, built by hand) and **Evidence** (case-study site with SQL
   and narrative, on GitHub Pages). Refresh on command, page shows "data as of".
4. **Python writes as a separate `pps-bot` user**, append-only and idempotent: every
   created record has a stable external ID; scripts never edit or delete records they
   didn't create.

## Next 3 steps
1. **Master data into `pps_live`:** products, BOMs, vendors, customers, reorder rules
   from `products/blg_whey_protein.yaml` through `ensure()`, with the diff-and-confirm
   sync for anything the user has since edited. Reuses the demo seed's logic.
2. **First data slice:** extract sales, purchase and manufacturing orders plus stock
   from `pps_live` into marts (DuckDB + CSV), stamped "data as of".
3. **Tableau MVP** on those marts: the user builds it; the loop is proven by creating a
   PO in the Odoo UI and watching it appear after a refresh.

The three-year history generator (`docs/plan-history-and-dashboard.md`, Phase 1) then
fills `pps_live` through the same append-only writer.

## Open questions
- Material cost: the history plan quotes $3.88/kg of powder, but the BOM against
  should-cost target prices gives **$2.33/kg** today. Resolve with a proper standard-cost
  roll-up before the ASP is set.
- Should-cost conversion and margin shares are mock; membrane life (ADR 0008) and DSP
  throughput (ADR 0006) are unsourced.
- See `knowledge/backlog.md`.
