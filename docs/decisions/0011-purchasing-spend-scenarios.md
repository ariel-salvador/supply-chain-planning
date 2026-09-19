# 0011: PO schedule from MRP; spend priced only from public series, with percentile scenarios

- **Status:** accepted (2026-09-18)
- **Context:** M3 turns planned releases of purchased items into purchase orders and
  estimates spend. Only corn and sugar have public price series (IMF via FRED).
  Nutrients, bags and membranes have none.
- **Decision:**
  - **POs:** one per vendor per release week. Each line is due at release + lead time.
    Vendors are the fictional ones in the config.
  - **Base price:** the latest monthly observation of the linked series, converted to
    USD per item unit by cited factors (corn content per kg glucose; cents/lb →
    USD/kg).
  - **Scenarios:** the 10th, 50th and 90th percentiles of monthly prices over a
    trailing window [mock: 10 years]. The percentiles are a statistical convention
    fixed in code (`purchasing.SCENARIOS`), not model data.
  - **Unpriced items:** listed as *excluded from spend* and never given invented
    prices.
- **Alternatives:** forecast prices (out of scope, and misleading without a model);
  price every item with estimates (breaks the citation rule); a single spot price (hides
  commodity volatility).
- **Consequences:**
  - Spend is a partial, feedstock-only figure, and outputs say so.
  - The glucose price is corn content only (topic `commodity-feedstocks`), so it's a
    floor.
  - Base case: 2.75 kt glucose over 26 weeks costs about $0.94M, with a 10–90 % range of
    $0.67M–$1.30M [estimate, mock demand].
