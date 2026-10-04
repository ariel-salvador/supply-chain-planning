# Hands-on ERP: Case 1 in Odoo 19 Community

This replicates the mock rBLG precision-fermentation plant in a real ERP. The data
comes only from `products/blg_whey_protein.yaml` and `knowledge/assumptions.csv`
(cited or [mock]). The company, vendors and customer are **fictional** and labeled
as such. Why Odoo Community, and what stays in Python: ADR 0009.

## Run it

Requirements: Docker (OrbStack or Docker Desktop) and the repo's `.venv`.

```bash
make odoo-demo        # rebuild from scratch: reset → up → init → seed → run → compare (~1 min)
```

| Step | Command | What it does |
|---|---|---|
| 1 | `make odoo-up` | Creates `.env` with random secrets if missing, then starts Postgres 17 and Odoo 19 on `127.0.0.1:8069` |
| 2 | `make odoo-init` | Creates the `pps_demo` DB (no demo data), installs Inventory, Manufacturing, Purchase and Sales, sets the admin password from `.env`, and writes a 7-day API key to `.odoo-apikey` |
| 3 | `make odoo-seed` | `scripts/odoo_seed.py`: company, units, products, routes, vendor lead times, BOMs, reorder rules, opening stock, open orders, weekly sales orders |
| 4 | `make odoo-run` | `scripts/odoo_run.py`: runs the scheduler and exports MOs and PO lines to `data/processed/odoo_plan.csv` |
| 5 | `make odoo-compare` | `scripts/compare_plans.py`: diffs against the Python MRP and writes [`comparison.md`](comparison.md) |

To sign in at http://127.0.0.1:8069, use the user `admin` and the password in your
local `.env` (`ODOO_ADMIN_PASSWORD`). `make odoo-down` stops the stack, and
`make odoo-reset` deletes it.

Secrets live in `.env` and `.odoo-apikey`, both gitignored. The database and
filestore live in Docker volumes and are never committed.

## How the config maps to Odoo

| Config | Odoo |
|---|---|
| items (`finished`/`intermediate`) | storable products with the **Manufacture** route |
| items (`purchased`) | storable products with the **Buy** route, plus one vendor price-list line **per bidder** (`price` = quote, `delay` = quoted lead time × 7 days, `min_qty` = MOQ, `sequence` = RFQ rank) |
| supplier master (`suppliers`) | one `res.partner` per bidder, all fictional |
| RFQ round | one **draft** purchase order per bidding supplier, `origin = "RFQ round [mock]"`; a draft PO *is* an RFQ in Odoo, and a quote is not a commitment |
| RFQ award | `sequence` 1 on the price list, so the scheduler replenishes from the awarded supplier; open POs are placed with it too |
| `batch_size` | BOM base quantity: powder per batch (13,636 kg); one fermentation batch (12,000 kg rBLG) |
| BOM lines | BOM components (qty × base); `produce_delay` = lead time in days |
| lot multiple / fixed order qty | a custom unit (e.g. *BLG-FERM batch (12,000 kg)*, *GLUCOSE lot (250,000 kg)*) set as the reorder rule's replenishment unit |
| safety stock | reorder rule min = max = safety stock, auto trigger |
| on hand | inventory adjustment |
| scheduled receipts | WIP MOs without a BOM (so no double consumption), and confirmed open POs |
| weekly demand (MPS projected demand) | one confirmed sales order per week; engine week 0 → the Monday after the run date |
| horizon (26 weeks) | company **replenishment horizon** = 182 days (Odoo's default is 365) |

> **Sourcing (M6) is code review only so far.** The price-list, RFQ and award mapping
> above was written without a running instance (ADR 0016); `make odoo-demo` is the check.
> The screenshots below and `comparison.md` predate it.

## What each screen shows (screenshots in this folder)

Captured from the local demo at 1200×720 (1.5× pixel ratio), cropped to the Odoo app.
They were checked for usernames, emails and file paths before committing.

| File | Screen | Shows |
|---|---|---|
| `bom.png` | Manufacturing → Products → Bills of Materials | Two-level BOM per batch with cited quantities |
| `reorder-rules.png` | Inventory → Operations → Replenishment | Min/max = safety stock and the batch/lot units |
| `replenishment-run.png` | Manufacturing → Manufacturing Orders, after the scheduler | Every planned MO starts *today* (reorder rules replenish the whole window now) |
| `mo.png` | A generated manufacturing order | Batch-multiple quantity and components reserved |
| `po.png` | A generated RFQ | Fictional vendor, lead-time due date, grouped lines |
| `comparison.png` | [`comparison.md`](comparison.md) rendered | Odoo vs engine quantities and timing |

## Odoo ↔ SAP S/4HANA: the same flow, different names

Odoo Community covers the core MRP transaction flow found in any ERP. This table maps
what this demo does to the SAP S/4HANA equivalents (transaction codes in brackets), so
the concepts carry over to SAP-based planning roles.

| Concept | Odoo (this demo) | SAP S/4HANA equivalent |
|---|---|---|
| Item master | Product (route, UoM, vendor list) | Material master [MM01], with MRP views |
| Bill of materials | BoM (one per batch) | BOM [CS01]; **master recipe** [C201] in process industries (PP-PI) |
| Vendor lead time / min qty | Vendor price list (`delay`, `min_qty`) | Purchasing info record [ME11]; planned delivery time on the material |
| Reorder rule | Reordering rule (min/max, auto) | MRP type on the material: reorder-point planning (e.g. VB) vs MRP (PD) |
| Lot sizing | Replenishment unit (batch or lot as a unit) | Lot-sizing procedure: lot-for-lot (EX), fixed (FX), rounding value |
| Planning run | Scheduler / Replenishment | MRP run [MD01N] and stock/requirements list [MD04] |
| Planned supply | MO or RFQ created directly | Planned orders, converted to production orders [CO40] or purchase requisitions |
| Manufacturing order | Manufacturing Order | Production order [CO01], or **process order** [COR1] for fermentation-type plants |
| Purchasing | RFQ → Purchase Order | Purchase requisition [ME51N] → purchase order [ME21N] |
| Demand | Confirmed sales orders | Sales orders [VA01] and planned independent requirements [MD61] |
| Master production schedule | Enterprise edition only | MPS strategies within MRP; PP/DS or IBP for advanced planning |
| Capacity planning | Enterprise (Gantt / work orders) | Capacity evaluation [CM01]; PP/DS for finite scheduling |

**How the planning logic compares:** Odoo's reorder rules behave like SAP
reorder-point planning. The Python engine's time-phased weekly plan behaves like SAP
MRP with planned independent requirements, and that's the difference quantified in
[`comparison.md`](comparison.md).

## What I learned

- **Reorder rules aren't MRP.** One scheduler run covers every shortfall inside the
  look-ahead window immediately. The engine's time-phased plan spreads the same volume
  over 26 weeks. In Community, time-phasing comes from running the scheduler daily with
  a short horizon; the MPS that would plan ahead is Enterprise-only.
- **Odoo plans reactively as well as on schedule.** Confirming each sales order
  triggered the auto reorder rules immediately, so most MOs existed before the
  scheduler even ran.
- **Units carry lot logic in Odoo 19.** Reorder rules no longer have a "multiple"
  field. A replenishment unit (12,000 kg batch, 250 t lot) does the job, and it keeps
  the batch visible to planners.
- **API migration matters.** XML-RPC/JSON-RPC are deprecated in 19, so this uses
  JSON-2 with a scoped, expiring API key created from `odoo shell`, with no clicks.
- **Odoo 19 changed several model details:** UoM categories were replaced by relative
  units; products use `type='consu'` plus `is_storable`; the manufacturing lead time
  lives on the BOM (`produce_delay`); the replenishment horizon is a company setting.
