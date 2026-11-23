# Plan: three years of history, then a dashboard

_Written 2026-11-23 as a cold-start handoff. Read this plus `docs/status.md` before
starting. Nothing in this plan is built yet._

## Goal

Backfill **2024-01-01 → today** of weekly operating history (sales, production,
purchasing, receipts, invoicing, inventory), then build a dashboard on it. The end
product is a **static page that can be linked from a job application** — a screener
will never log into a local Odoo, so Odoo is where the data is generated and validated,
not where the deliverable lives.

## Why: what the current demo cannot show

Every supply chain KPI is a time series, and the demo has none. Not computable today:
inventory turns, days of supply, OTIF trend, PPV vs standard, forecast accuracy
(MAPE/bias), schedule attainment. Those are the questions interviewers ask.

## Diagnosis of the current state (verified 2026-11-19 against the running stack)

1. **All 26 sales orders carry `date_order = 2026-11-16`** — the seed run date. The seed
   sets `commitment_date` (the delivery week) but lets `date_order` default to creation
   time, and **Odoo's Sales Analysis pivots on `date_order`**. So every chart collapses
   into one bar. Same for Purchase Analysis.
2. **`account.move` count is 0.** There is no invoicing at all — no customer invoices, no
   vendor bills, no AR. Invoicing is net new, not a backfill.
3. **No selling price exists anywhere in the repo.** Products are created without
   `list_price`, so Odoo defaults to $1.00/kg and `amount_total` comes out ~$33K on
   30,000 kg. Material cost is **$3.88/kg of powder** (computed from the BOM against
   `should_cost.target_price_usd`), so revenue currently charts *below material cost*.
   **An ASP assumption is a prerequisite for any of this.**

## Phases

### Phase 1 — history generator (engine side), ~3–4 hrs
New `src/ppsim/history.py`. A weekly ledger 2024-01-01 → today: shipments by customer,
production batches, component consumption, receipts by supplier, on-hand by item, and the
KPI series. Plus the ASP assumption and standard costs, plus tests. Writes
`data/processed/history_*.csv`.

**This is the dependency for both later phases and it carries no Odoo risk.** Do it first.

### Phase 2 — Odoo backfill, ~4–5 hrs
New `scripts/odoo_history.py` + `make odoo-history`. ~2,600 documents, batched creates,
15–30 min runtime. Not part of `make odoo-demo`.

### Phase 3 — dashboard, ~3–4 hrs
Six panels off the Phase 1 CSVs, rendered static, following the existing
`reports/build_report.py` pattern: (1) sales/demand incl. forecast vs actual, (2)
production and capacity utilisation, (3) purchasing spend and PPV, (4) inventory value,
days of supply and turns, (5) supplier OTIF and fill rate, (6) revenue, COGS, margin, AR
aging.

## Decisions already made

| Decision | Value |
|---|---|
| Granularity | **Weekly**, 151 periods. Daily would be 1,050 periods and ~15,000 documents, and charts identically once rolled to months |
| Growth | Reuse the existing `mock_demand_growth` = **0.15/yr** with the existing seasonality and noise |
| Trend anchor | Anchor the trend at `cfg.start`, **not** `index[0]`, so the forward plan stays unchanged. Add an optional `anchor` arg to `demand.generate()` defaulting to `index[0]` |
| RNG | **A separate history seed.** `generate()` draws `len(index)` noise values, so a longer index would shift which value lands on each forward week and change the committed comparison. Generate history and forward separately |
| Volume | 2024 starts at 30,000 ÷ 1.15³ ≈ **19,700 kg/week**, reaching 30,000 by Jan 2027 |
| ASP | New **mock** assumption, built bottom-up with the existing `should_cost` method (material + conversion + margin), cross-checked against commodity whey isolate. Lands ~**$14/kg** → ~$22M revenue 2024 → ~$33M 2026 |
| **Hard rule** | **Nothing in the past stays open.** Every historical PO received and billed, MO done, SO delivered and invoiced. A draft PO counts as replenishment in progress (see ADR 0016) — an open 2024 PO would silently suppress the forward plan |
| Closing stock | History lands on a **physical inventory adjustment** snapping to the engine's assumed `on_hand`. That is a real ERP event, not a fudge |
| AR | Most invoices paid, a few left open, so receivables aging is chartable |

## Known Odoo constraints (Odoo 19 Community)

**Writable for backdating:** `sale.order.date_order`, `purchase.order.date_order`,
`account.move.invoice_date` and `.date` (on draft, then post), `stock.move.date` and
`stock.picking.date_done` (after validation).

**Not writable:** `stock.valuation.layer.create_date` is immutable by design, so Odoo's
Inventory Valuation report will show every layer as today no matter what. **Derive the
historical inventory value from the movement ledger instead** — we know every receipt
quantity × cost and every issue exactly — and record the limitation in an ADR.

## Housekeeping to clear first

- Branch **`odoo-partner-lists`** is 2 commits ahead of `main` and **unpushed**:
  `4999ce0` (vendor/customer split, five fictional customers) and `4a603ed` (functional
  partner names). **169 tests pass.**
- Uncommitted: `data/processed/odoo_plan.csv`, `docs/odoo/comparison.md` — regenerated
  output from the 2026-11-19 verification run.
- Four remote branches verified **fully merged into `origin/main`** and safe to delete.
  The permission classifier blocks this for the agent; the user runs it:
  `git push origin --delete m-odoo m1-foundation m2-sop-mps m4-rccp`

## Deprioritised by the user (2026-11-16)

The public report variant and the two M6 screenshots (RFQ round, multi-vendor price
list). Also scoped but parked: a "week driver" agent to run the ERP as a live mock
company (~5 phases, 10–14 hrs).
