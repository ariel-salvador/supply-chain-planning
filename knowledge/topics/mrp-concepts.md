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

## Next layers

- **S&OP → MPS (M2):** monthly aggregate plan broken down to weekly MPS, with time
  fences (frozen/slushy/liquid) and available-to-promise.
- **Purchasing (M3):** planned releases of purchased items become POs, priced from FRED.
