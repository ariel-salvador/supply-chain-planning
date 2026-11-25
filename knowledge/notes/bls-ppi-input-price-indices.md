# BLS producer price indices (via FRED) for the non-commodity inputs

- **Source:** US Bureau of Labor Statistics, Producer Price Index, as published on FRED
  (Federal Reserve Bank of St. Louis). Monthly, not seasonally adjusted.
- **URLs:** `https://fred.stlouisfed.org/series/<id>` (CSV:
  `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<id>`)
- **Retrieved:** 2026-11-25 (observations through 2026-10)
- **License:** BLS data are US government works (public domain); FRED asks for a citation.
  Still cached under `data/raw/` and not committed, like the IMF series (ADR 0003).
- **Reliability:** official statistics. They measure **US producer price movement for an
  industry or commodity group**, not the price of our exact input: they are proxies.
- **reviewed:** false

## Series used (ADR 0018; `sourcing.should_cost.material_index`)

| Input | Series | Title on FRED | Fit |
|---|---|---|---|
| Ammonia, ammonium sulfate | `PCU325311325311` | PPI by Industry: Nitrogenous Fertilizer Manufacturing | good: ammonia is the industry's core product |
| Potassium phosphate, magnesium sulfate, calcium chloride | `PCU325180325180` | PPI by Industry: Other Basic Inorganic Chemical Manufacturing | fair: right industry group, broad basket |
| 25 kg multiwall paper bag | `PCU322220322220` | PPI by Industry: Paper Bag and Coated and Treated Paper Manufacturing | good |
| UF/DF membrane set (PES) | `PCU326199326199` | PPI by Industry: All Other Plastics Product Manufacturing | weak proxy: no membrane-specific series found |

Candidates checked and not used: `WPU0652` fertilizer materials (broader than nitrogen),
`WPU0613` basic inorganic chemicals (commodity basis, close alternative), `WPU0913`
paper (not converted bags), `WPU1149` misc. general-purpose equipment.

## How it is used

`price(month) = mock base × index(month) / index(2026-01)`. The **level** stays the
labeled mock base (`mock_base_*` rows) at January 2026; the **movement** before and
after is the published index. So the history's purchase prices, standard costs and the
quarterly list price move like the real markets did (e.g. the nitrogen fertilizer
index rose roughly 40-50% from early 2025 to mid-2026), without inventing a dollar price.
