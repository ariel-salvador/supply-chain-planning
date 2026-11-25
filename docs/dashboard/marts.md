# Marts: the tables the dashboards read

Built by `make dashboard-extract` (live, as the read-only `pps-reader`) or
`make dashboard-extract SOURCE=demo`. Output: `outputs/marts/<database>/`, one CSV per
table for **Tableau** and `pps.duckdb` with the same tables for **Evidence**. Gitignored:
the marts are rebuilt from Odoo on demand; `meta.extracted_at_utc` says when.

Join everything on the `*_id` columns: `product_id` → `dim_product`, `customer_id` /
`vendor_id` → `dim_partner`. `week` is the Monday of the ISO week (the planning engine's
bucket). `created_by` on every document: `script` (pps-bot or a stable `x_pps_key`),
`manual` (someone in the Odoo UI) or `demo` (the disposable demo database).

| Table | Grain (one row per…) | Key columns | Main measures | Date / week from |
|---|---|---|---|---|
| `dim_product` | product | `product_id`, `product_code`, `name`, `uom_id`, `uom_name` | `sale_ok`, `purchase_ok`, `is_storable` | — |
| `dim_partner` | company partner | `partner_id`, `name`, `role` (supplier / customer / other) | `supplier_rank`, `customer_rank`, `created_by` | — |
| `fact_sales` | sales order line | `line_id`, `order_ref`, `product_id`, `customer_id`, `state`, `created_by` | `qty_ordered`, `qty_delivered`, `price_unit`, `amount` | `date_order`, `date_promised` → `week` |
| `fact_purchases` | purchase order line | `line_id`, `order_ref`, `product_id`, `vendor_id`, `state`, `origin`, `created_by` | `qty_ordered`, `qty_received`, `price_unit`, `amount` | `date_order`, `date_planned` → `week` |
| `fact_production` | manufacturing order | `mo_id`, `mo_ref`, `product_id`, `state`, `origin`, `created_by` | `product_qty`, `qty_produced` | `date_start`, `date_finished` → `week` |
| `fact_stock` | product × internal location (snapshot) | `quant_id`, `product_id`, `location_id`, `location_name` | `quantity`, `reserved_quantity` | snapshot at `meta.extracted_at_utc` |
| `fact_reorder` | reorder rule (snapshot) | `orderpoint_id`, `product_id`, `trigger` | `product_min_qty`, `product_max_qty`, `qty_on_hand`, `qty_forecast`, `qty_to_order` | snapshot |
| `meta` | extraction | `extracted_at_utc`, `database` | `rows_<table>` per table | — |

**Notes**
- `origin` marks special documents: `… at start [mock]` = starting work-in-progress and
  open POs from the demo seed; `RFQ round [mock]` = the sourcing round's draft quotes.
  Filter them out for "planned" volumes.
- Snapshots (`fact_stock`, `fact_reorder`) describe the moment of extraction. Time series
  of stock come later, from the history generator's movements.
- Values are mock or derived from cited public data (`knowledge/assumptions.csv`). Any
  published chart built on prices carries the IMF/FRED citation (ADR 0003).
