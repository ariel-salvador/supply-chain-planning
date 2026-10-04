# Status (handoff)

_Last updated: 2026-10-04 · branch `m6-sourcing` (from `main` after PR #5; local only,
not pushed). Repo is private._

## Current milestone
**M6 sourcing is built** (6a–6f in the engine, 6g in the Odoo seed). `main` has M1–M5
and the Odoo demo (PR #1–#5). M6 is on `m6-sourcing`, waiting for review and push.

## Done (this block)
- **M6a supplier master** (ADR 0012): a `suppliers:` block in the config — 12 fictional
  bidders, three per material family, from three mock archetypes (incumbent, low-cost,
  premium) with per-supplier overrides, each with a lane, incoterm, risk tier and quoted
  terms. `vendors:` keeps its M3 meaning; the **award** now decides who the POs go to.
- **M6b RFQ → award** (ADR 0013): price / lead time / quality / risk, range-normalised
  inside each bid set and weighted 45/15/25/15 [mock policy], with a written rationale
  per item naming the criterion that decided it. Three different suppliers win: the
  incumbent takes sugar and membranes, the premium supplier the nutrients, the low-cost
  supplier packaging.
- **M6c should-cost** (ADR 0014): material + conversion + margin, with `material_basis`
  recording whether material came from the cited commodity index or a mock base. The
  awarded glucose quote sits at should-cost; the nutrient awards sit +9%.
- **M6d TCO** (ADR 0014): freight and duty by incoterm, MOQ carrying cost, cost of
  defects. **On all 9 items the lowest quote is not the lowest total cost** — every
  cheapest bid is an import bid.
- **M6e scorecard** (ADR 0015): a simulated 12-period delivery history per awarded
  supplier → OTIF, on-time, in-full, fill rate, lead-time sigma and purchase price
  variance against standard cost, with A–D grades.
- **M6f strategy** (ADR 0015): single vs dual source priced against the expected value
  of supply at risk (no backfill assumed), the safety-stock cost of lead-time variance,
  and forward buy vs spot passed through at the material share of the build-up. Glucose
  forward buy breaks even at $0.480/kg against a p50 of $0.434 and a p90 of $0.599.
- **M6g Odoo mirror** (ADR 0016): price-list lines per bidder with the awarded supplier
  at `sequence` 1, and the RFQ round as draft purchase orders marked
  `origin = "RFQ round [mock]"`, excluded from the plan comparison. **Not verified
  against a running instance** — Docker was unavailable; the payload builders are pure
  functions and are tested.
- **Report:** 5 new charts (RFQ scorecard, should-cost vs quotes, TCO stack, delivered
  vs quoted OTIF, forward buy vs spot) and 2 tiles. 13 charts total.
- **Also:** 58 new registry rows — 57 mock and one cited (`service_level_z`), 128 total
  with 109 used by case 1; `knowledge/topics/sourcing-concepts.md`; **164 tests pass**
  (111 before M6).

## In progress
- Nothing open. Waiting for review of `m6-sourcing`.

## Next 3 steps
1. With the user's OK: pre-push check, push `m6-sourcing`, PR #6, merge.
2. **Verify M6g:** `make odoo-demo`, then regenerate `docs/odoo/comparison.md` and the
   screenshots (add one of the RFQ round and one of a multi-vendor price list).
3. Public-facing report variant: publish charts with mock/cited data plus derived cost
   (with IMF citation), without the raw price series. Decide hosting with the user first.

## Open questions
- The should-cost conversion and margin shares are mock; public cost structures would
  replace the two weakest rows in the registry.
- Membrane life (ADR 0008) and DSP throughput (ADR 0006) are still unsourced.
- Should the award feed back into the planning lead time automatically? Today it is a
  note for a human.
- See `knowledge/backlog.md`.
