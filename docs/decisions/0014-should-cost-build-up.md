# 0014: should-cost as material + conversion + margin; TCO adds landed, MOQ and quality cost

- **Status:** accepted (2026-10-04)
- **Context:** the question a buyer gets asked is "should this part cost what they are
  charging?" Answering it needs a bottom-up cost, not a benchmark against last year's
  price.
- **Decision:**
  - Per quoted item: **material + conversion + (SG&A and margin) = target price**,
    on an ex-works basis. Conversion is a share of material cost and margin a share of
    material + conversion [both mock], so one build-up serves every item.
  - **Material** is the latest value of the item's linked price index when there is one
    (glucose → corn via FRED/IMF, sucrose → ICE No. 11), else a mock base cost. The
    `material_basis` column records which, verbatim, in every output.
  - Inbound **freight and duty are not** part of should-cost: they depend on the
    supplier's lane and incoterm, so they belong to TCO. This keeps the quote and the
    target on the same basis.
  - `material_share` is carried forward so a commodity move can be passed through at
    the material share of the price, which is what an index-linked price clause does.
  - **Total cost of ownership** then adds, per supplier, what the quote does not say:
    - **freight and duty by incoterm** (`config.INCOTERMS`): under EXW and FOB the
      buyer pays both, under CIF and DAP the seller delivers but the buyer clears
      customs, under DDP the seller pays both. Freight and duty are shares of the
      ex-works cost for the supplier's lane [mock], duty charged on quote + freight;
    - **MOQ carrying cost:** half the minimum order quantity is average cycle stock,
      carried at the annual rate and spread over annual volume;
    - **cost of defects:** the defect rate times a mock multiple of the purchase price,
      because a rejected unit costs more than its price.
    The outputs rank each item's bidders by price and by TCO and list the items where
    the two disagree, which in case 1 is every item with an import bid.
- **Alternatives:** a single mock cost per item (no build-up, nothing to negotiate
  with); should-cost with freight included (not comparable to an ex-works quote);
  estimating conversion per item (more rows, no better founded).
- **Consequences:**
  - The gap to quote is only as good as the conversion and margin shares, which are
    mock; the *method* is the deliverable, not the dollar figure.
  - For glucose the material line is corn content only (topic `commodity-feedstocks`),
    so the target price is a floor and the gap to quote is an upper bound.
