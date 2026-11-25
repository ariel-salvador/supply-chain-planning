# Changelog

How the project grew, one entry per merged milestone. Work before 2026-11-24 happened in
a private repository; its commits carried over unchanged (same dates and messages), and
these entries summarise the pull requests that merged them.

## 2026-11-25: Three years of operating history in the live ERP
- `src/ppsim/history.py`: a weekly mock ledger, 2024-01 to 2026-11. Demand grows into the
  plan, whole fermentation batches run within capacity, reorder-point buying uses the
  awarded suppliers' late and short rates, and invoices and payments follow customer
  behaviour. Named events: a contaminated batch, a supplier outage, a demand spike.
- Prices move like real markets: FRED corn for glucose, BLS producer price indices for
  the other inputs, standard costs rolled each January, a quarterly list price with
  customer discounts.
- `make odoo-history` writes it into `pps_live` as ~3,200 backdated, closed documents
  (resumable, append-only); `make odoo-history-rehearse` tries it on a copy first;
  `scripts/check_history.py` proves Odoo matches the ledger. The extract gains invoices,
  payments, stock moves, forecast, standard costs and the price list.

## 2026-11-25: Read-only extract for the dashboards
- `make dashboard-extract` reads Odoo into tidy marts (CSV for Tableau, DuckDB for
  Evidence): products, partners, sales, purchases, production, stock and reorder rules,
  with week buckets and who created each document (script vs manual).
- Runs as `pps-reader`, read-only on the server (a custom group) and in the client (a
  `ReadOnlyOdoo` that refuses any write). Data dictionary in `docs/dashboard/marts.md`.

## 2026-11-25: Master data in the live ERP
- `make odoo-live-master` loads the case-1 master data into `pps_live` (65 records:
  units, partners, products, vendor price lists, BOMs, reorder rules) as `pps-bot`.
- Append-only and idempotent: reruns create nothing. A value changed in the Odoo UI is
  reported as a diff and left alone; `APPLY_DIFFS=1` reverts it to the config.
- Reorder rules use the manual trigger in the live system, so the planner runs
  replenishment rather than every sales order firing it.

## 2026-11-24: Dashboard Phase 0, Odoo as the system of record
- Two databases: `pps_demo` (disposable, rebuilt by `make odoo-demo`, which no longer
  deletes volumes) and `pps_live` (the system of record, never dropped).
- `scripts/odoo_admin.py`: guarded operations. `drop` refuses `pps_live`; `nuke`
  refuses without a fresh verified backup; backups in Odoo's zip format (database +
  filestore), verified on write; a restore test that proves the latest backup loads.
- Scripts write as a least-privilege `pps-bot` user through an append-only
  `ensure()`: stable `x_pps_key` per record, never edits or deletes, so manual work in
  the UI is never overwritten. Verified: the bot can't escalate its rights, and a full
  demo rebuild leaves `pps_live` identical.

## 2026-11-24: Public launch prep
- Repository renamed to **Supply Chain Planning**; commit identities normalised to the
  author's GitHub noreply address.
- `scripts/pre_push_check.py` now blocks any push whose commits use a non-noreply author
  or committer email, on every commit (not just the latest).
- Launch checklist, README opening, "How this was built", this changelog.

## 2026-11-23: Partner lists and the history plan
- Vendors and customers kept as separate lists; five fictional customer segments with
  functional names (food brand, beverage, sports nutrition, distributor, co-packer).
- Plan for three years of weekly operating history and a KPI dashboard
  (`docs/plan-history-and-dashboard.md`).

## 2026-11-12: M6, sourcing and supplier management
- Supplier master: 12 fictional bidders from three archetypes (incumbent, low-cost,
  premium), each with a lane, incoterm, risk tier and quoted terms.
- RFQ scoring and award on price, lead time, quality and risk, with a written rationale
  per item.
- Should-cost build-up (material + conversion + margin) and total cost of ownership
  (freight, duty, MOQ carrying cost, quality). The cheapest quote is not the lowest TCO
  on any of the 9 items.
- Supplier scorecard (OTIF, fill rate, lead-time variability, PPV) and strategy:
  single vs dual source, forward buy vs spot.
- Mirrored into Odoo and verified there; the run found two real issues (a draft RFQ
  suppresses replenishment; vendor selection respects MOQ) and both were fixed.

## 2026-10-04: Odoo ↔ SAP S/4HANA mapping
- Table mapping each Odoo concept in the demo to its SAP S/4HANA equivalent and
  transaction code (`docs/odoo/README.md`).

## 2026-09-19: M4 capacity, M3 purchasing, M5 report
- **M4:** rough-cut capacity with a bill of resources; pull-forward leveling cuts peak
  fermenter load from 119% to 89%.
- **M3:** purchase-order schedule from MRP; spend priced from FRED-linked commodity
  prices with p10/p50/p90 scenarios. Unpriced items are excluded, never guessed.
- **M5:** self-contained HTML chart report (`make report`).

## 2026-09-19: ERP, Case 1 in Odoo 19 Community
- Local Odoo 19 Community + Postgres stack (pinned images, localhost only, secrets in a
  gitignored `.env`); one command rebuilds it from scratch.
- Seeded from the product config through Odoo's JSON-2 API: products, routes, per-batch
  BOMs, vendors, reorder rules, stock, open orders, weekly sales orders.
- Comparison with the Python MRP: quantities agree within 7–9%; Odoo's reorder rules
  order the whole horizon up front while MRP phases it weekly.

## 2026-09-18: M2, S&OP → MPS
- Monthly S&OP (chase or level) capped by capacity; weekly MPS with demand and planning
  time fences, projected available balance and available-to-promise; MPS drives MRP.

## 2026-09-18: M1, foundations
- Planning engine: config loader that rejects uncited process numbers, BOM explosion,
  time-phased MRP with lot sizing and safety stock.
- FRED commodity prices (corn, sugar), seeded mock demand, cited process parameters for
  a precision-fermentation whey protein plant.
- Assumptions registry, research notes, ADRs, licences (MIT code, CC BY docs).
