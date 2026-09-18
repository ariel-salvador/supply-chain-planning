# FRED / IMF Primary Commodity Prices: corn and sugar

- **Series:** `PMAIZMTUSDM` Global price of Corn (USD per metric ton), and
  `PSUGAISAUSDM` Global price of Sugar, No. 11, World (US cents per lb). Both are
  monthly, not seasonally adjusted, and period averages in nominal USD.
- **URLs:** https://fred.stlouisfed.org/series/PMAIZMTUSDM ,
  https://fred.stlouisfed.org/series/PSUGAISAUSDM
- **CSV (no key):** `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`
- **Retrieved:** 2026-09-18 (data 1992-01 to 2026-07)
- **License:** copyrighted by the IMF and reprinted by FRED with permission; citation
  required. **Don't commit the raw data.** Fetch it at runtime into the gitignored cache.
- **reviewed:** false

## Practical notes

- Benchmark prices are set by the largest exporter of each commodity. That makes them a
  global proxy, not a delivered price at any plant.
- FRED's CSV endpoint stalls some custom or browser User-Agents. urllib's default UA,
  curl and wget all work (tested 2026-09-18).
- Missing values show up as `.`.
