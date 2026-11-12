# Sourcing concepts as implemented (M6)

How the sourcing module works and why, in the vocabulary a buyer or sourcing analyst
uses. Code: `src/ppsim/sourcing.py`, `src/ppsim/supplier_perf.py`. Decisions:
ADR 0012–0016. Everything about suppliers here is **[mock]**; commodity prices are
**[source]** (IMF via FRED).

## Where sourcing sits

Planning answers *how much* and *when*: S&OP → MPS → MRP → planned order releases.
Sourcing answers *who from* and *at what cost*, and it is the step that turns a planned
release into a purchase order with a price on it.

```
MRP planned releases ─► planned usage (volume to quote)
                            │
should-cost target price ◄──┤  commodity index (cited) or mock base
                            ▼
                         RFQ: bids scored on price / lead time / quality / risk
                            ▼
                        award ─► price list + PO ─► delivery performance ─► PPV
                            ▼
                        strategy: single vs dual source, forward buy vs spot
```

## Supplier master (M6a)

One record per **bidder**, not per item: lane (origin), incoterm, risk tier, and the
quoted terms — price, lead time, minimum order quantity (MOQ), defect rate in parts per
million, on-time-in-full (OTIF) rate, lead-time standard deviation, short-ship rate.
A buyer needs all of it: the first four decide the award, the last three decide whether
the award was right.

**Qualified source** means a supplier the quality system has approved for that material.
In a regulated plant (cGMP, 21 CFR 210/211) switching to an unqualified source is not a
purchasing decision at all; it requires qualification first. The simulator takes the
supplier master as already qualified and says so.

## Should-cost (M6c)

> *Should this part cost what they are charging?*

Built bottom-up: **material + conversion + (SG&A and margin) = target price**, on an
ex-works basis. Material comes from a public commodity index where one exists (corn for
glucose, ICE No. 11 for sucrose), otherwise a labelled mock base. The difference
between the target and the quote is the **negotiation gap** — the number you take into
the conversation, instead of "last year you charged less".

Freight and duty are deliberately **not** in should-cost: they depend on the lane and
the incoterm, so they belong in total cost (below). Keeping them out means quote and
target are on the same basis.

`material_share` matters on its own: it is what an **index-linked price clause** passes
through. If material is 73% of the price, a 10% commodity move justifies 7.3%, not 10%.

## RFQ, scoring and award (M6b)

Weights are fixed **before** bids are opened (price 45%, quality 25%, lead time 15%,
risk 15% [mock policy]), then each criterion is **range-normalised** inside the bid set:
best = 1, worst = 0. Normalising is the whole point of a scorecard — it puts ppm, weeks
and dollars on one scale so the weights decide, not the units.

Consequences worth saying out loud in an interview: the worst bid scores 0 on that
criterion however small the real gap is, and with only two bidders the loser scores 0 on
everything it loses. A three-bidder set is the minimum that makes the method behave.

Every award carries a written **rationale**: winner, runner-up, score margin, the
criterion with the largest weighted gap between them, what the lowest bid lost on, and
the gap to should-cost. If the award cannot be explained in one sentence, it is not
defensible.

## Total cost of ownership (M6d)

The quote is not the cost. TCO adds:

| Element | Why it moves the ranking |
|---|---|
| **Inbound freight and duty, by incoterm** | A FOB price excludes the freight the buyer then pays; a DDP price already includes it. Comparing them as quoted compares different things. |
| **MOQ carrying cost** | A big minimum order buys cycle stock you finance: half the MOQ, at the carrying rate, spread over annual volume. |
| **Cost of defects** | A rejected unit costs more than its price: inspection, rework, a stopped line, a deviation to write. |

**Incoterms** in the model (`config.INCOTERMS`): EXW and FOB — buyer pays freight and
duty; CIF and DAP — seller delivers, buyer clears customs and pays duty; DDP — seller
pays both. In case 1 the cheapest quote on every item is an import bid, and on every
item it loses on total cost.

## Supplier performance (M6e)

- **OTIF** — on time *and* in full. Both conditions, one number, and it is the number a
  supplier review opens with.
- **Fill rate** — share of ordered quantity actually received.
- **Lead-time variance** — the planner's problem, not the buyer's trophy: it is paid for
  in safety stock, `z × sigma_lead_time × demand per period`, carried at the inventory
  rate all year.
- **Purchase price variance (PPV)** — (invoiced price − standard cost) × quantity.
  Negative is favourable. Standard cost here is the awarded quote, so PPV measures drift
  away from what was awarded, which is the question a buyer is actually asked.
- **Grades** A ≥ 95%, B ≥ 90%, C ≥ 80%, else D — a common convention, fixed in code.

A 12-period sample has a wide confidence interval, so measured OTIF can land well off
the quoted figure. The scorecard reports both and the difference between them.

## Category strategy (M6f)

- **Single vs dual source.** Priced, not asserted: the extra annual cost of splitting
  volume against the **expected value of supply at risk** (probability of disruption ×
  weeks lost × usage × share). No backfill is assumed, so dual sourcing only reduces
  exposure when the second source is no riskier than the first. State the assumption —
  if the alternate can cover, the answer changes.
- **Forward buy vs spot.** Buying coverage ahead costs the carrying charge on the
  average inventory held; it pays only if the spot price rises past that breakeven. The
  price scenarios (p10/p50/p90 of the commodity index, ADR 0011) say how likely that is,
  and the material share says how much of the quote actually moves with the index.

## Vocabulary, briefly

**PPV** purchase price variance · **MOQ** minimum order quantity · **OTIF** on time in
full · **RFQ/RFP** request for quotation / proposal · **TCO** total cost of ownership ·
**should-cost** bottom-up target price · **landed cost** price + freight + duty ·
**incoterm** who pays and bears risk at each point of the shipment · **dual sourcing**
splitting volume across two qualified suppliers · **standard cost** the frozen price
variances are measured against · **qualified source** a supplier quality has approved
for that material.
