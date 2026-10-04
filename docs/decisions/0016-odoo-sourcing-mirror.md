# 0016: mirror sourcing in Odoo with multi-vendor price lists and draft RFQs only

- **Status:** accepted (2026-10-04), **not yet verified against a running instance**
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
  - **The sourcing round → draft purchase orders.** In Odoo a draft `purchase.order`
    *is* a request for quotation, so each bidding supplier gets one RFQ listing the
    items it quoted at the horizon volume the award was decided on. They stay **draft**:
    a quote is not a commitment, and the real POs come from the scheduler.
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
- **Consequences:**
  - A buyer can open Purchase → Requests for Quotation in the demo and see the bid
    round, then see the generated POs go to the awarded supplier.
  - **Unverified:** written without a running Odoo (Docker was not available in that
    session). `make odoo-demo` is the check; until someone runs it, treat the Odoo part
    of M6 as code review only. The pure functions are tested; the API calls are not.
