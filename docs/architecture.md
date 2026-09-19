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
- **Built (M4):** RCCP loads fermenter hours from planned batch starts and levels
  overloads by pulling batches earlier (ADR 0010).
- **Built (M3):** purchasing turns planned releases of purchased items into POs, priced
  from FRED with percentile scenarios (ADR 0011).
- **Built (M5):** `reports/build_report.py` renders a self-contained HTML report
  (dependency-free SVG charts with tooltips, table views, light/dark) from engine
  results. It stays local because it embeds IMF-derived prices (ADR 0003).
- **Planned:** DSP capacity once sourced; a public report variant without raw price series.

## Engine modules

| Module | Responsibility |
|---|---|
| `registry.py` | load/validate `assumptions.csv` (status, confidence, citation fields) |
| `config.py` | load product YAML; safe expression evaluator; enforce cited-only process math, id-only planning numbers, `used_in` |
| `demand.py` | seeded mock demand (trend × seasonality × noise), always labeled mock |
| `sop.py` | week↔month weights, aggregation/disaggregation, chase/level plan with capacity |
| `mps.py` | projected demand (DTF), planning-fence catch-up (PTF), PAB, ATP, mock order book |
| `rccp.py` | bill of resources, load vs capacity per bucket, pull-forward leveling |
| `purchasing.py` | PO schedule (vendor × release week), spend from linked prices, p10/p50/p90 scenarios |
| `bom.py` | low-level codes, cycle detection, explosion, summed requirements |
| `mrp.py` | netting, lot sizing (LFL / FOQ / POQ / min / multiple), safety stock, lead-time offset, past-due |
| `fred.py` | FRED CSV download + cache with retrieval metadata |
| `feedstock.py` | FRED series → USD per item uom → feedstock cost per finished unit |
| `pipeline.py` / `cli.py` | orchestration, CSV + manifest output |
