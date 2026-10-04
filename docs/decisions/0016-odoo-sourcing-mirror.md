# 0016: mirror sourcing in Odoo with multi-vendor price lists and draft RFQs only

- **Status:** accepted (2026-10-04), **verified against Odoo 19.0 Community the same day**
  (`make odoo-demo`); revised after the first run failed
- **Context:** M6 decides who to buy from. The Odoo demo should execute that decision
  the way a buyer would, using only Odoo 19 **Community** (ADR 0009) and the four apps
  already installed (`stock`, `mrp`, `purchase`, `sale_management`).
- **Decision:**
  - **Supplier master → `res.partner`:** every bidder is created, not just the
    incumbent. All names are fictional and say so.
  - **Quotes → `product.supplierinfo`:** one price-list line per (item, bidder) with
    the quoted `price`, `delay` (quoted lead time in days) and `min_qty` (the MOQ), and
    `sequence` set to the RFQ rank. Odoo replenishes from the lowest-sequence line, so
    **sequence 1 = the awarded supplier** makes the award the default source without
    any custom code. The award also sets the partner on the seeded open POs.
  - **The sourcing round → draft purchase orders, created after the planning run.** In
    Odoo a draft `purchase.order` *is* a request for quotation, so each bidding supplier
    gets one RFQ listing the items it quoted at the horizon volume the award was decided
    on. They stay **draft**: a quote is not a commitment, and the real POs come from the
    scheduler. It lives in its own script (`scripts/odoo_sourcing.py`, `make odoo-rfq`)
    that runs **after** `odoo-run` and `odoo-compare`, for the reason in the first
    finding below.
  - **The RFQ round is marked** `origin = "RFQ round [mock]"`. `odoo_run.py` exports it
    with an `rfq` flag and `compare_plans.py` excludes it, so the engine-vs-Odoo
    comparison still compares plans and not quotations.
  - **No purchase agreements (blanket orders).** `purchase.requisition` is a separate
    module that would have to be installed, and its fields differ across versions. The
    price list already carries price, MOQ and lead time per vendor, which is what the
    plan needs. Left in `knowledge/backlog.md`.
  - The payload builders (`supplier_prices`, `rfq_lines` in `scripts/odoo_seed.py`) are
    **pure functions** so what Odoo would receive is covered by offline tests.
- **Alternatives:** install `purchase_requisition` for real agreements (more moving
  parts, version-sensitive, no planning benefit); confirm the winning RFQ into a PO
  (would double-count against the scheduler's own POs); keep one vendor per item as in
  M3 (then Odoo cannot show the award at all).
- **What the first run found (both fixed):**
  1. **A draft RFQ is replenishment already in progress.**
     `stock.warehouse.orderpoint` counts draft, sent and to-approve purchase lines in
     `_quantity_in_progress`, so seeding one RFQ per bidder at the horizon volume told
     Odoo that three times the requirement was already on order. Every orderpoint's
     `qty_to_order` fell to 0 and the scheduler raised **no purchase orders at all** —
     the glucose forecast sat at +7.2 Mkg — which turned the plan comparison from
     "within 7-9%" into -100% on every purchased item, with no error logged anywhere.
     Fixed by moving the round after the planning run. The award does not need the
     documents: it is already on the price list, which is what drives replenishment.
  2. **Vendor selection respects the MOQ, so an award can quietly stop applying.**
     Odoo picks the lowest-`sequence` price-list line whose `min_qty` the order reaches.
     Bags are awarded to a supplier quoting six weeks of cover (MOQ 6,918 units) while
     the plan orders weekly (393-1,630 units), so Odoo skipped it on 13 of 22 lines and
     bought from the runner-up instead. That is correct ERP behaviour and the **engine
     was the thing that was wrong**: it assigned every PO to the awarded supplier
     regardless of quantity. `sourcing.check_moq` now flags it (`below_awarded_moq` on
     the PO lines, plus a note when the typical order is more than 10% under the MOQ),
     and `compare_plans.py` prints an award-honoured column per item.
- **Consequences:**
  - A buyer can open Purchase → Requests for Quotation in the demo and see the bid
    round, and `docs/odoo/comparison.md` shows, per item, whether the generated POs went
    to the awarded supplier. Verified run: 6 of 7 items honoured the award; bags did not,
    for the MOQ reason above.
  - **The RFQ round must stay last.** Once those drafts exist, re-running the scheduler
    raises no new POs until they are confirmed or cancelled. `odoo_sourcing.py` says so
    on exit, the Makefile target documents it, and a test asserts the ordering.
  - A sourcing award and a lot-sizing policy are one decision, not two. The MOQ check is
    the engine's half of what the ERP enforces.
