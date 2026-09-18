# 0002: Every number lives in an assumptions registry; configs reference ids

- **Status:** accepted (2026-09-18). Supersedes the M1 design, where cited values sat
  inline in the product YAML.
- **Context:** The repo will be public, and it must be obvious which numbers are
  sourced, estimated or made up. It also can't contain anyone's workplace data.
- **Decision:** `knowledge/assumptions.csv` (id, name, value, unit, low, high, source,
  url, retrieved, confidence, status, used_in) is the single store of model numbers.
  Product YAML references ids. The loader enforces:
  (a) BOM quantities and price conversions rest only on `cited` rows (directly or via
  `derived` expressions); (b) planning and demand values are ids (mock), and only `0` may
  be literal; (c) expressions contain no numeric literals except 0 and 1; (d) each id
  lists the product in `used_in`.
- **Alternatives:** inline values with a citation block per parameter (the M1 approach:
  readable, but numbers are scattered across files); a database (overkill).
- **Consequences:** Configs read as structure. Unit constants (kg/t, cents/USD, h/week)
  become registry rows too. `scripts/pre_push_check.py` can audit everything in one place.
