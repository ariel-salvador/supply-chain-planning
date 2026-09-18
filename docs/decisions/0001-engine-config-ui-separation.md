# 0001: Separate engine, product config and UI

- **Status:** accepted (2026-09-18)
- **Context:** The simulator must handle more than one product. Results should first be
  published as static charts, and an interactive UI may follow.
- **Decision:** `src/ppsim/` is a pure-Python/pandas engine with no product names,
  numbers, plotting or web imports. Each product is one YAML file. Reports and any UI
  consume engine outputs (DataFrames/CSVs).
- **Alternatives:** notebook-first (fast, but mixes logic and presentation and is hard
  to test); a web app from day one (heavy, delays publishable results).
- **Consequences:** Engine logic is unit-testable offline. A new product needs no code.
  Charts need a small `reports/` layer.
