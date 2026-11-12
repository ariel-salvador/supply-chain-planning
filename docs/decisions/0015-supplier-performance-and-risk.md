# 0015: simulated delivery history for the scorecard; exposure-based sourcing strategy

- **Status:** accepted (2026-10-04)
- **Context:** a supplier scorecard and a single/dual-source decision both need
  performance history, which a mock plant does not have. It has to be simulated, and
  the simulation has to be labelled and reproducible.
- **Decision:**
  - **Delivery history** (`supplier_perf.delivery_history`): one row per simulated
    period per awarded supplier, from `sourcing.seed`. How often a delivery is late
    comes from the supplier's quoted OTIF, not from a second parameter:
    `P(on time) = OTIF / (1 - short-ship rate)`, so the simulated OTIF reproduces the
    quoted one. How late it is comes from the lead-time sigma, with a floor of one
    bucket. Invoiced price drifts around standard cost by a mock CV, which is where
    **purchase price variance** comes from. Standard cost is the awarded quote.
  - **Grades** (A ≥ 95%, B ≥ 90%, C ≥ 80%, else D) are a buyer convention fixed in
    code (`supplier_perf.GRADES`), not model data — as the price percentiles are in
    ADR 0011.
  - **Safety-stock cost:** `z × sigma_lead_time × demand per bucket`, valued at the
    landed price and carried at the annual rate. Lead-time variability is treated as the
    only source of variance here; demand variability is the MPS's job.
  - **Single vs dual source:** annual cost from TCO against the **expected value of
    supply at risk** = `P(disruption) × weeks lost × usage per bucket × share`, valued
    at the *awarded* landed price for every share so that a pricier second source does
    not look riskier merely for costing more. `P = disruption_prob_base × (1 - risk
    score)`. Dual sourcing splits the volume and **no backfill is assumed**: if one
    source stops, its share stops.
  - **Forward buy vs spot:** forward cost per unit = quote + carrying on the average
    inventory held over the coverage window; the spot comparison passes each price
    scenario (ADR 0011) through at the material share of the build-up (ADR 0014).
- **Alternatives:** fixed OTIF without a history (no PPV, no fill rate, no variance);
  a disruption *loss* model (needs a cost of lost production, which this repo has no
  basis for); assuming the alternate source backfills (would make dual sourcing look
  good by assumption).
- **Consequences:**
  - A 12-period sample has a wide confidence interval, so simulated OTIF can land well
    off the quoted figure. The scorecard reports `otif_vs_quoted` rather than hiding it.
  - The no-backfill assumption means dual sourcing only reduces exposure when the
    second source is no riskier than the first. In case 1 that holds for packaging and
    membranes and fails for the nutrients, where the runner-up is a medium-risk source
    against a low-risk winner. A backfill assumption would reverse those conclusions,
    which is exactly why it is stated here.
  - Every performance figure is **mock** and the outputs, CLI and report say so.
