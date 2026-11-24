# Changelog

How the project grew, one entry per merged milestone. Work before 2026-11-24 happened in
a private repository; its commits carried over unchanged (same dates and messages), and
these entries summarise the pull requests that merged them.

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
