# Production Planning Simulator

A product-agnostic production planning engine covering
**S&OP → MPS → MRP → purchasing → rough-cut capacity planning (RCCP)**. Each product is
described by one config file.

**Case 1:** a *mock* precision-fermentation plant making recombinant
beta-lactoglobulin (rBLG) whey protein powder. The feedstock prices are real (IMF
commodity series via FRED), the process parameters come from cited public literature,
and **the demand is mock**.

> Portfolio project. It contains no personal information and no company's internal
> data. All process parameters come from public sources listed in
> [`products/blg_whey_protein/SOURCES.md`](products/blg_whey_protein/SOURCES.md).

## Status

| Milestone | Scope | State |
|---|---|---|
| **M1** | FRED data pull, mock demand generator, BOM, basic MRP table | ✅ done |
| M2 | S&OP (monthly, aggregate) → MPS (weekly), ATP, time fences | planned |
| M3 | Purchasing: PO schedule, feedstock spend vs. FRED history, price scenarios | planned |
| M4 | RCCP: bioreactor-hours / DSP load vs. capacity, batch lot sizing | planned (needs working-volume source) |
| M5 | Static charts (published first), then optional interactive UI | planned |

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/python -m ppsim run products/blg_whey_protein/product.yaml
.venv/bin/python -m ppsim run products/blg_whey_protein/product.yaml --variant sucrose
```

Outputs go to `outputs/<product>[-<variant>]/`: `demand_mock.csv`,
`bom_explosion.csv`, `mrp_<ITEM>.csv`, `mrp_long.csv`, `parameters.csv` (every value
with its citation), `feedstock_*.csv`, and `manifest.json` (sources, FRED retrieval
metadata, warnings).

## How it works

```
product.yaml ──► config loader ──► demand generator (mock) ──► MRP ──► CSV outputs ──► static charts
  cited params     rejects uncited      seeded, labeled          │
  derived exprs    parameters                                    ▼
  items / BOM                         FRED CSV (cached) ──► feedstock prices ──► cost per kg
```

- **Engine** (`src/ppsim/`): pure Python + pandas, no plotting or UI imports.
- **Configs** (`products/<id>/product.yaml`): items, BOM, planning policies, demand
  spec, and `parameters:` that each need a `source` and `locator`. Derived values are
  arithmetic expressions over cited parameters, so every BOM quantity can be traced to
  a source.
- **MRP**: gross → net → lot-size (lot-for-lot, fixed order quantity, periods of
  supply, min/multiple) → lead-time offset, processed in low-level-code order, with
  safety stock and past-due flags.

## Case 1 at a glance (per kg of powder)

| Step | Quantity | Basis |
|---|---|---|
| rBLG secreted in fermentation | 0.880 kg | 85.8 % rBLG in product ÷ 97.5 % MF recovery |
| Glucose (or sucrose) fed | 4.38 kg | 0.223 g protein/g sugar, 90 % rBLG share |
| Corn, as glucose feedstock | ≥ 7.05 kg | EPA AP-42 starch yield + hydrolysis stoichiometry |

## Repository layout

```
src/ppsim/        engine
products/         one folder per product (config + sources)
tests/            pytest, offline
reports/          static chart scripts (M5)
data/cache/       FRED cache (gitignored, IMF-copyrighted data)
outputs/          run outputs (gitignored)
```

## Data sources and licensing

- Behm et al. (2022), *Int J Life Cycle Assess* 27:1017–1034, CC BY 4.0.
- US EPA AP-42 §9.9.7 Corn Wet Milling.
- IMF Primary Commodity Prices via FRED: `PMAIZMTUSDM`, `PSUGAISAUSDM`. These are
  copyrighted by the IMF and must be cited. They're fetched at runtime and not
  redistributed in this repo.

## License

TBD.
