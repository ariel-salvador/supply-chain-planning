# Production Planning Simulator

A product-agnostic production planning engine covering
**S&OP → MPS → MRP → purchasing → rough-cut capacity planning (RCCP)**. Each product is
one config file.

**Case 1:** a *mock* precision-fermentation plant making recombinant
beta-lactoglobulin (rBLG) whey protein powder. The feedstock prices are real (IMF
commodity series via FRED), the process parameters are cited from public literature,
and **the demand is mock**.

> Portfolio project. No personal information and no company's internal data. Every
> model number lives in [`knowledge/assumptions.csv`](knowledge/assumptions.csv) with
> its status (`cited` / `estimate` / `mock`), source and retrieval date.

## Status

| Milestone | Scope | State |
|---|---|---|
| **M1** | FRED data pull, mock demand generator, BOM, basic MRP table | ✅ done |
| M2 | S&OP (monthly, aggregate) → MPS (weekly), ATP, time fences | planned |
| M3 | Purchasing: PO schedule, feedstock spend vs. FRED history, price scenarios | planned |
| M4 | RCCP: bioreactor-hours / DSP load vs. capacity, batch lot sizing | planned (needs a working-volume source) |
| M5 | Static charts (published first), then an optional interactive UI | planned |

Details: [`docs/status.md`](docs/status.md) · map of all docs: [`INDEX.md`](INDEX.md).

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/python scripts/fetch_data.py                     # FRED → data/raw/ (not committed)
.venv/bin/python -m ppsim run products/blg_whey_protein.yaml
.venv/bin/python -m ppsim run products/blg_whey_protein.yaml --variant sucrose
```

Outputs go to `outputs/<product>[-<variant>]/`: `demand_mock.csv`,
`bom_explosion.csv`, `mrp_<ITEM>.csv`, `mrp_long.csv`, `parameters.csv` (every number
used, with status and citation), `feedstock_*.csv`, and `manifest.json`.

## How it works

```
knowledge/assumptions.csv ─► config loader ─► mock demand ─► MRP ─► outputs/*.csv ─► static charts
products/<id>.yaml ─────────┘  (rejects uncited               ▲
                                process numbers)              │
FRED CSV ─► data/raw/ ─► feedstock prices ─► cost per kg ─────┘
```

- **Engine** (`src/ppsim/`): pure Python + pandas, no plotting or UI imports.
- **Configs** (`products/<id>.yaml`): items, BOM, policies and demand spec, written as
  *assumption ids*, never raw numbers. BOM quantities are expressions over `cited`
  ids, and the loader enforces that.
- **MRP:** gross → net → lot-size (lot-for-lot, fixed order quantity, periods of supply,
  min/multiple) → lead-time offset, in low-level-code order, with safety stock and
  past-due flags.

More: [`docs/architecture.md`](docs/architecture.md), and the decisions in
[`docs/decisions/`](docs/decisions/).

## Case 1 at a glance (per kg of powder)

| Step | Quantity | Basis |
|---|---|---|
| rBLG secreted in fermentation | 0.880 kg | 85.8 % rBLG in product ÷ 97.5 % MF recovery [source → derived] |
| Glucose (or sucrose) fed | 4.38 kg | 0.223 g protein/g sugar, 90 % rBLG share [source → derived] |
| Corn, as glucose feedstock | ≥ 7.05 kg | EPA AP-42 starch yield + hydrolysis stoichiometry [source → derived] |

Process background: [`knowledge/topics/precision-fermentation-process.md`](knowledge/topics/precision-fermentation-process.md).

## Data sources and licensing

- Behm et al. (2022), *Int J Life Cycle Assess* 27:1017–1034, CC BY 4.0.
- US EPA AP-42 §9.9.7 Corn Wet Milling.
- IMF Primary Commodity Prices via FRED: `PMAIZMTUSDM`, `PSUGAISAUSDM`. These are
  copyrighted by the IMF and must be cited. They're fetched at runtime and not
  redistributed here (see `scripts/fetch_data.py`).

## License

- **Code** (everything outside `docs/` and `knowledge/`): [MIT](LICENSE).
- **Documentation and research content** (`docs/`, `knowledge/`):
  [CC BY 4.0](LICENSE-docs). Reuse is welcome with attribution to
  *agenttofu0, production-planning-simulator*.
- **Third-party material is not covered by either license.** Cited papers, EPA
  documents and the IMF/FRED price series keep their own terms. The price data is
  not redistributed here, and published charts must cite "International Monetary
  Fund, retrieved from FRED, Federal Reserve Bank of St. Louis."
