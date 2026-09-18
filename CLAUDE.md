# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo.

## What this is

A portfolio project: a **product-agnostic production planning simulator** that chains
S&OP → MPS → MRP → purchasing → rough-cut capacity planning (RCCP).
Case 1 is a **mock** precision-fermentation plant making recombinant
beta-lactoglobulin (rBLG) whey protein powder.

## Hard rules

1. **No personal info, no employer data.** Nothing from any real company's internal
   systems, plans, costs, or processes. If a number can't be traced to a public source,
   it doesn't go in as a process parameter.
2. **Process parameters must cite a public source.** Every entry under `parameters:` in a
   product config needs `source` (a key in that file's `sources:`) and `locator`
   (table/section/page). The loader rejects configs that violate this — don't weaken
   that check. Derived values go under `derived:` as expressions of cited parameters.
3. **Mock data is labeled as mock.** Demand, starting inventory, lot sizes, safety stock
   and non-process lead times are *planning assumptions*, not facts. They live under
   `demand:` / `items[].planning` with `basis: assumption`, and every output that
   depends on them says so.
4. **Engine ≠ UI.** `src/ppsim/` must not import plotting or web libraries. Charts and
   any future UI live in `reports/` (or a separate app) and consume engine outputs
   (DataFrames / CSVs). Static charts come first.
5. **Product-agnostic engine.** No product-specific names, numbers, or branches in
   `src/ppsim/`. A new product = a new folder under `products/` with a `product.yaml`
   and a `SOURCES.md`.
6. **FRED/IMF data is not committed.** The commodity series are copyrighted by the IMF
   and redistributed by FRED with a citation requirement. Fetch at runtime into
   `data/cache/` (gitignored); cite the series in any published chart.
7. **Git:** work on branches, commit locally, **never push without asking.**

## Layout

```
src/ppsim/          engine (pure Python + pandas; no plotting)
  config.py         load + validate product YAML; safe expression evaluator
  fred.py           FRED CSV download with on-disk cache (no API key)
  demand.py         seeded mock demand generator
  bom.py            BOM model, low-level codes, multi-level explosion
  mrp.py            time-phased MRP records (lot-for-lot, FOQ, POQ, min/multiple)
  feedstock.py      map FRED price series onto purchased items
  pipeline.py       runs the milestone chain, writes CSVs
  cli.py            `python -m ppsim ...`
products/<id>/      one folder per product: product.yaml + SOURCES.md
tests/              pytest; no network (FRED tests use fixtures)
reports/            (later) static chart scripts that read outputs/
data/cache/         runtime FRED cache (gitignored)
outputs/            run outputs (gitignored)
```

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/python -m ppsim run products/blg_whey_protein/product.yaml --out outputs/blg
.venv/bin/python -m ppsim run products/blg_whey_protein/product.yaml --offline   # cache only
```

## Conventions

- Python ≥ 3.9 (system Python on the dev machine is 3.9): use
  `from __future__ import annotations`, no `match`, no `X | Y` at runtime.
- Quantities in the item's `uom` (kg for everything in Case 1). Periods are pandas
  `Period`s at the config's `time.freq`; the engine works on integer bucket indices.
- MRP rows use the textbook names: gross requirements, scheduled receipts, projected
  on hand, net requirements, planned order receipts, planned order releases.
- Keep functions pure (inputs → DataFrame). I/O only in `fred.py`, `pipeline.py`, `cli.py`.
- Add a test for every planning rule you add; hand-checkable textbook examples preferred.
