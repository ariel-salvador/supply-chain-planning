# MRP concepts as implemented in `ppsim`

This covers standard time-phased MRP logic (in the tradition of Orlicky's MRP). It's
here so readers can check the engine against the textbook. No model numbers.

## Record (per item, per bucket)

| Row | Meaning |
|---|---|
| gross requirements | independent (mock) demand + parents' planned releases × qty_per |
| scheduled receipts | open orders already released |
| projected on hand | end-of-bucket inventory after planned receipts |
| net requirements | shortfall below safety stock before new receipts |
| planned order receipts | net requirement after lot sizing |
| planned order releases | receipts shifted earlier by the item's lead time |

## Rules

- **Low-level codes:** an item is planned only after every parent, at its deepest BOM
  level, so its gross requirements are complete (`bom.low_level_codes`).
- **Netting:** available = previous POH + scheduled receipts − gross. If available is
  below safety stock, net = SS − available.
- **Lot sizing:** lot-for-lot; fixed order quantity (multiples of Q); periods of supply
  (covers the next *P* buckets); then minimum and multiple constraints.
- **Offsetting:** release = receipt bucket − lead time. Releases that would land before
  bucket 0 are **past due**. They're flagged, and still charged to components in
  bucket 0 so component demand isn't lost.
- **Pegging / capacity:** not yet. Capacity comes via RCCP (M4).

Hand-checked examples live in `tests/test_mrp.py`.

## S&OP and MPS (M2, `sop.py`, `mps.py`)

- **S&OP (monthly):** aggregate demand → production plan meeting a target ending
  inventory (months of cover of next month's rate), `chase` or `level`, capped by
  capacity; flags stockouts, capacity limits and below-target months.
- **Disaggregation:** monthly plan → weeks in proportion to forecast; straddling weeks
  are split by days.
- **MPS record:** forecast, customer orders, projected demand, firm MPS, planned MPS,
  projected available balance (PAB), available-to-promise (ATP), zone.
- **Time fences:** DTF (orders-only demand inside) and PTF (no new planned MPS inside;
  PTF ≥ DTF). Zones are frozen, slushy and liquid.
- **ATP (discrete, look-ahead):** at each receipt week, the receipt (plus on hand in
  week 0) minus orders until the next receipt; negatives are borrowed from earlier
  receipt weeks.
- **Link to MRP:** the MPS becomes the finished item's planned receipts; MRP explodes
  it to components.

Decisions: ADR 0006 (capacity basis), ADR 0007 (linkage details).

## RCCP (M4, `rccp.py`)

- **Bill of resources:** hours per unit of an item on a resource. Load = planned
  releases × hours per unit, placed in the release week.
- **Capacity** = units × hours per week × availability. Utilization = load / capacity,
  and overloaded = load > capacity.
- **Leveling:** pull whole lots to the latest earlier week with spare capacity, within
  `max_pull_forward`, then re-run MRP with leveled receipts fixed. Residual overloads
  are warnings. ADR 0010.

## Next layers

- **Purchasing (M3):** planned releases of purchased items become POs, priced from FRED.
- **RCCP for DSP:** add bill-of-resources lines once throughput is sourced.
