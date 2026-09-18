# Commodity feedstocks: corn/glucose and sugar prices

Notes: `notes/fred-imf-commodity-prices.md`, `notes/epa-ap42-corn-wet-milling.md`,
`notes/unit-constants.md`.

## Series

| Series | What | Units | Tag |
|---|---|---|---|
| `PMAIZMTUSDM` | IMF global corn benchmark | USD / metric ton, monthly | [source] |
| `PSUGAISAUSDM` | IMF global sugar No. 11 | US cents / lb, monthly | [source] |

These are IMF-copyrighted: fetched at runtime, never committed, cited on charts
(ADR 0003).

## Conversions (all registry ids)

- **Corn → glucose:** 25 kg bushel → 14 kg starch (`corn_per_bushel`,
  `starch_per_bushel`) [source]. Starch → glucose gains 180.156 / 162.141 = 1.111 in mass
  [source: stoichiometry]. So **≥ 1.607 kg corn per kg glucose** [estimate: theoretical
  minimum with 100 % hydrolysis and no refining losses].
- The glucose "price" is therefore **corn content only**. It excludes wet-milling,
  refining and freight, so it's a floor, not a dextrose market price.
- **Sugar:** USD/kg = cents/lb ÷ 100 ÷ 0.45359237 [source].

## Result (M1 run, July 2026 prices, retrieved 2026-09-18)

Feedstock-only cost per kg of powder is about **$1.50 with glucose** (corn basis) and
about **$1.43 with sucrose** [estimate: cited process ratios × FRED prices]. Both
exclude processing, energy and all other costs.

## Caveats

- These are global benchmark prices, not delivered prices at any plant.
- For M3, find a public dextrose/glucose syrup price series or a published wet-milling
  cost (see backlog).
