# Status (handoff)

_Last updated: 2026-11-25 · repo **`ariel-salvador/supply-chain-planning`**, **public**
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

- **Master data loaded into `pps_live`** (2026-11-25): 65 records via
  `make odoo-live-master`; reruns create nothing; UI edits are reported, not reverted.
  Reorder rules are manual-trigger (ADR 0017 amendment).

- **Extract built** (2026-11-25): `make dashboard-extract` (live, read-only `pps-reader`)
  or `SOURCE=demo` → `outputs/marts/<db>/` (CSV + DuckDB), documented in
  `docs/dashboard/marts.md`. Live has master data only until transactions exist; the
  demo extract has 26 weeks of orders.

- **History generator built** (2026-11-25, ADR 0018): `src/ppsim/history.py` simulates
  2024-01-01 → 2026-11-22 (weekly; every item balances every week) and
  `make odoo-history` writes it into `pps_live` as backdated documents: ~500 sales orders,
  ~170 purchase orders, ~540 manufacturing orders, deliveries, receipts, invoices, bills
  and payments. Prices move with real indices (FRED corn; BLS producer price indices for
  the other inputs); the list price resets quarterly. Rehearsed first on a copy
  (`make odoo-history-rehearse`), checked against the ledger by `scripts/check_history.py`.
- **Tableau: on hold** until the user creates a Tableau Public account. The data is ready:
  `make dashboard-extract` → `outputs/marts/pps_live/*.csv`, now with invoices, payments,
  stock moves, forecast, standard costs and the price list (`docs/dashboard/marts.md`).

## Next 3 steps
1. **Tableau MVP** (user, once the account exists): build from the live marts. Suggested
   first views: revenue and margin by quarter, OTIF and PPV by supplier, inventory and
   days of supply by week, AR aging.
2. **Evidence site** on the same marts, embedding the Tableau dashboard.
3. **Week driver** (parked idea): advance `pps_live` one week at a time from the plan,
   so the history keeps growing past 2026-11-22.

## Open questions
- Resolved: the plan doc's $3.88/kg material cost was the mock glucose fallback (ADR 0018).
- Should-cost conversion and margin shares are mock; membrane life (ADR 0008) and DSP
  throughput (ADR 0006) are unsourced.
- See `knowledge/backlog.md`.
