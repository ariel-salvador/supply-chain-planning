# 0013: RFQ scoring by range-normalised weighted criteria; quotes as a should-cost index

- **Status:** accepted (2026-10-04)
- **Context:** an award has to be defensible: a buyer must be able to say why the
  winner won and why the cheapest bid lost. That needs criteria on a common scale,
  weights fixed before the bids are opened, and a written rationale.
- **Decision:**
  - **Criteria and weights:** price, lead time, quality (defect ppm) and supply risk,
    weighted by `sourcing.weights`. The loader rejects a weight set that does not sum
    to 1 or that uses other keys. Case 1 uses price 45%, quality 25%, lead time 15%,
    risk 15% [mock policy].
  - **Normalisation:** range (min-max) inside each item's bid set — best = 1, worst = 0
    (`sourcing.range_score`). This is the standard weighted-scorecard method: it puts
    every criterion on one scale so the weights, not the units, decide. Known
    consequences, documented in the function: the worst bid scores 0 however small the
    real gap is; with only two bidders the loser scores 0 on everything it loses; a
    criterion every bid ties on scores 1 for all of them and so cannot separate them.
  - **Rationale:** generated per item, naming the winner, the runner-up, the score
    margin, the criterion with the largest weighted gap between the two, what the
    lowest bid lost on, and the gap to should-cost.
  - **Quotes are MOCK**, simulated as `price_index × should-cost target price` rather
    than invented dollar figures. In a real RFQ the quote is an input and should-cost is
    an independent estimate; here the index keeps the two linked so the comparison is
    reproducible without fabricating supplier pricing. Outputs and the report say so.
- **Alternatives:** ratio scoring (`best / x`), which keeps relative distances but lets
  one criterion with a wide spread — defect ppm, typically — dominate regardless of its
  weight; z-scores (unstable in sets of three); lowest price wins (no risk or quality
  view); independent dollar quotes per supplier (invented data).
- **Consequences:**
  - The award can be re-derived from the scored quote table by hand, which is the point.
  - Because quotes key off should-cost, a change in the commodity index moves every
    quote for that item together and leaves the ranking unchanged.
  - Weights are a policy lever: shifting weight to price flips the packaging and
    nutrient awards, which is worth demonstrating rather than hiding.
