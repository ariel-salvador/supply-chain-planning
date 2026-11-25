# 0018: Three years of mock operating history, written into the ERP

- **Status:** accepted (2026-11-25).
- **Context:** Every KPI a planning or buying role is judged on (inventory turns, days of
  supply, OTIF, forecast error, purchase price variance, capacity use, receivables) is a
  time series. `pps_live` had master data and no transactions. The plan
  (`docs/plan-history-and-dashboard.md`) called for a backfill from 2024-01-01.
- **Decision:**
  1. **The engine decides, Odoo records.** `src/ppsim/history.py` simulates the plant week
     by week (pure, tested: every item balances every week). `scripts/odoo_history.py`
     replays it in date order into Odoo as `pps-bot`, as real documents: purchase
     orders, receipts, vendor bills and payments; manufacturing orders and one scrap;
     sales orders, deliveries, customer invoices and payments. 3,162 steps for case 1.
  2. **Window:** 2024-01-01 to 2026-11-22, the last full week before the backfill, fixed
     in the config. Every key derives from it (`hist:so:<customer>:<week>`), so a rerun
     is a no-op and the history never shifts under the user's own work.
  3. **Nothing in the past stays open.** Every order due by the end is delivered or
     received, invoiced or billed. Open at the end, as in a real business: orders due
     after it (two weeks of customer orders, a few purchase orders in transit),
     receivables not yet paid (recent, or from the slow-paying distributor), and bills
     not yet due.
  4. **Demand** backcasts the plan's own trend: `demand.generate` gains an `anchor` (the
     plan's start) and a `seed` (a separate stream), so demand grows from ~19,700 to
     ~30,000 kg/week, into the forward plan's base, and the forward plan is unchanged.
     It is split over the five fictional customers by mock share and cadence. Orders
     ship whole, in 25 kg bags (cited bag size), first due first.
  5. **Production:** whole 12,000 kg fermentation batches, at most 3 a week (the
     bill-of-resources limit of 3.36), sized so powder stays above safety stock after the
     booked orders; each batch becomes powder the next week.
  6. **Purchasing:** reorder point per item from the RFQ-awarded supplier, with its quoted
     lead time and minimum order in weeks of usage. Deliveries are late or short at the
     supplier's quoted OTIF, lead-time sigma and short-ship rate (the sourcing records).
     Short deliveries close without a backorder and are billed as received.
  7. **Prices move like real markets** (requested by the user, 2026-11-25):
     - **Glucose** is bought at the month's **cited** FRED corn price, through the
       should-cost build-up, times the supplier's quote index.
     - **Every other input** keeps its mock base *level* but moves month to month with a
       **cited US producer price index** (BLS via FRED): nitrogen fertilizer for ammonia and
       ammonium sulfate, other inorganic chemicals for the salts, paper bags, and plastics
       products as a weak proxy for membranes (`knowledge/notes/bls-ppi-input-price-indices.md`).
     - **Standard costs are rolled every January** from the prior December's prices, as
       most manufacturers do; PPV is actual minus standard, so it swings with the markets.
     - The **selling price** is a list price **reset every quarter** from the prior month's
       cost (material + a mock $7.50/kg conversion) grossed up by a mock 30% target margin
       (about $13.60–14.40/kg over the window). The two weekly key accounts get 3% off and
       the distributor 6% (mock). Margin therefore moves between resets.
  8. **Named events** (mock, in the config): a contaminated fermentation batch, scrapped
     (March 2025); a four-week glucose supplier outage with emergency buys from the
     runner-up (August 2025); an unforecast six-week beverage launch (May 2026).
  9. **The plan doc's $3.88/kg material cost was the mock fallback.** Without FRED prices
     the should-cost uses `mock_base_glucose` ($0.60/kg). With the cited corn index,
     material is about $2.2–2.3/kg of powder. The master-data loader ran without prices, so
     `pps_live` vendor price lists carried the fallback. It now loads the cited prices,
     plus each product's standard cost and the powder's current list price.
- **How Odoo is made to tell the truth about dates:** documents are created, confirmed and
  validated, then their dates are written back: order dates (confirming stamps "now"),
  picking and move dates, invoice and accounting dates. Done manufacturing orders refuse
  date changes unless Odoo's own `force_date` context is set; the backfill sets it.
  Chatter tracking is switched off, so the backfill doesn't log thousands of messages.
- **Permissions:** the bot gains *Invoicing / Billing* (`account.group_account_invoice`):
  invoices, bills and payments, with no accounting configuration, users or settings. The
  reader gains read access to payments, journals and scraps.
- **Rehearsal first:** `make odoo-history-rehearse` loads the latest `pps_live` backup
  into the disposable `pps_demo` and writes the history there. The live run
  (`make odoo-history`) always takes a verified backup first.
- **Alternatives:** *Daily granularity* (15,000+ documents, charts the same once rolled
  up). *Creating accounting entries directly* (skips the operational documents the
  dashboard and the user work with). *Leaving the plan-doc ASP of $14/kg as a bare
  number* (the house rule: every number traces to a registry id). *Random noise around
  fixed prices* (moves, but not like any real market).
- **Consequences / limits:**
  - Inventory valuation in Odoo is periodic (Community default), so there are no stock
    journal entries. Inventory value over time comes from the stock moves times the
    yearly standard cost (`fact_stock_moves`, `dim_standard_cost`).
  - Odoo has no statistical forecast. The forecast the history was planned against is
    exported with the ledger (`outputs/history/forecast.csv`) and joined in the marts.
  - FRED publishes monthly with a lag; months after the last observation carry the last
    price forward, and the run prints a note saying so.
  - Customer service is near-perfect by design (orders are booked two weeks ahead, which
    matches the production lead time). Service problems in the story come from the
    events and from supplier lateness, not from forecast misses.
