# Architecture

## Three layers

| Layer | Where | Knows about |
|---|---|---|
| **Knowledge** | `knowledge/assumptions.csv`, `knowledge/notes/` | numbers and their sources |
| **Config** | `products/<id>.yaml` | one product's items, BOM, policies, and which assumption ids it uses |
| **Engine** | `src/ppsim/` | planning logic only, no product names or numbers |
| **Reports / UI** | `reports/` (static charts first), optional app later | reads engine outputs (CSV / DataFrames) |

The engine never imports plotting or web code, so results can be published as static
charts first and a UI can be added later without touching planning logic (ADR 0001).

## Data flow

```
FRED CSV ──(scripts/fetch_data.py, ppsim.fred)──► data/raw/ ──► feedstock prices ──┐
                                                                                    │
assumptions.csv ─► config loader (validates citations) ─► ProductConfig             │
                                                             │                      │
                     mock demand ─► S&OP (M2) ─► MPS (M2) ─► MRP (M1) ─► POs (M3) ─► RCCP (M4)
                                                             │           │           │
                                                             └──── outputs/*.csv + manifest.json ──► reports/
```

- **Built (M1):** assumptions registry → config → mock demand → BOM → MRP, plus FRED
  prices → feedstock cost per kg.
- **Built (M2):** S&OP (monthly, chase/level, capacity-capped) → MPS (weekly, time
  fences, PAB, ATP) → MRP with the MPS as the finished item's planned receipts
  (ADR 0007).
- **Planned:** purchasing turns planned releases of purchased items into POs priced
  from FRED; RCCP loads batch starts and DSP against capacity.

## Engine modules

| Module | Responsibility |
|---|---|
| `registry.py` | load/validate `assumptions.csv` (status, confidence, citation fields) |
| `config.py` | load product YAML; safe expression evaluator; enforce cited-only process math, id-only planning numbers, `used_in` |
| `demand.py` | seeded mock demand (trend × seasonality × noise), always labeled mock |
| `sop.py` | week↔month weights, aggregation/disaggregation, chase/level plan with capacity |
| `mps.py` | projected demand (DTF), planning-fence catch-up (PTF), PAB, ATP, mock order book |
| `bom.py` | low-level codes, cycle detection, explosion, summed requirements |
| `mrp.py` | netting, lot sizing (LFL / FOQ / POQ / min / multiple), safety stock, lead-time offset, past-due |
| `fred.py` | FRED CSV download + cache with retrieval metadata |
| `feedstock.py` | FRED series → USD per item uom → feedstock cost per finished unit |
| `pipeline.py` / `cli.py` | orchestration, CSV + manifest output |
