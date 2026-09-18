# 0008: Allow [mock] BOM quantities for non-process consumables

- **Status:** accepted (2026-09-18), approved by the repo owner. It narrows ADR 0002.
- **Context:** The Odoo demo needs UF/DF membranes as a consumable. No public source was
  found for membrane life or replacement rate (searched 2026-09-18: Behm 2022,
  Humbird 2011, Cunniffe 2025, dairy UF literature). Packaging *was* sourced (USDA DME1,
  25 kg bags) and nutrients were sourced (Humbird Table 20), so those stay `cited`.
- **Decision:** A BOM line may set `basis: mock` **only** when its component item has
  `category: consumable`. Its quantity must still be an expression of registry ids
  (here `mock_batches_per_membrane_set`, status `mock`). All other BOM lines must rest
  on `cited` ids, as before. The loader enforces both.
- **Alternatives:** leave membranes out (the Odoo BOM would be less realistic);
  invent a "typical" lifetime and label it `estimate` (misleading without a source).
- **Consequences:** The BOM explosion shows the line's expression, and the registry
  row says mock. If a public membrane-life source turns up, change the row to `cited`
  and drop the `basis: mock` flag.
