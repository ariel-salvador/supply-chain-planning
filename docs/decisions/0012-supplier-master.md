# 0012: a supplier master in the config, separate from the Odoo vendor list

- **Status:** accepted (2026-10-04)
- **Context:** M3 had one vendor per purchased item (`vendors:`), which is all the Odoo
  demo needs. Sourcing is about choosing *between* suppliers, so an item needs several
  bidders, each with its own price, lead time, minimum order quantity, origin lane,
  incoterm, quality record and risk tier.
- **Decision:**
  - A new `suppliers:` block is the **supplier master**: every bidder, with a `quote`
    (price index, lead-time delta, MOQ in weeks of cover, defect ppm, OTIF, lead-time
    sigma, short-ship rate), a `lane`, an `incoterm` and a `risk_tier`. Every supplier
    must be marked `fictional: true`, as `vendors:` and `customers:` already are.
  - `vendors:` **stays** and keeps its M3 meaning (the incumbent list the Odoo seed
    loads). The award decides who the POs actually go to: `purchasing.po_schedule`
    takes an optional item → supplier map, which `sourcing.awarded_vendor_map` builds.
  - The case-1 master is **three bidders per material family** (sugar, nutrients,
    packaging, membranes) built from three MOCK archetypes — incumbent, low-cost,
    premium — because defining 12 independent suppliers would mean ~80 more registry
    rows for no extra insight. Two suppliers override archetype terms (`s_nutr_b`,
    `s_pack_b`) so the award is not the same story on every item: as configured the
    incumbent wins sugar and membranes, the premium supplier wins the nutrients and the
    low-cost supplier wins packaging.
  - Quoted lead time = the item's planning lead time + the supplier's delta, floored at
    one bucket. MOQ = the supplier's weeks of cover × planned usage per bucket, so the
    MOQ scales with the plan instead of being a second set of mock quantities.
- **Alternatives:** extend `vendors:` with quote fields (would have broken the M3
  one-vendor-per-item mapping and the Odoo seed); a separate CSV of quotes (puts model
  numbers outside the registry); independent numbers per supplier per item (more rows,
  no more insight).
- **Consequences:**
  - Choosing the mock archetypes so that three different suppliers win is a deliberate
    demo choice, stated here so it is not mistaken for a result.
  - A supplier's quote is the same across the items it supplies, so an RFQ outcome can
    only differ between items through lead time, MOQ and volume. Per-item quotes would
    need per-item registry rows.
  - When the awarded lead time differs from the planning parameter, the run says so in
    `sourcing_notes` rather than silently re-planning.
