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
| `dim_partner` | company partner (archived ones too) | `partner_id`, `name`, `role` (supplier / customer / other), `supplier_status` (preferred / approved), `tags`, `active` | `supplier_rank`, `customer_rank`, `created_by` | — |
| `fact_sales` | sales order line | `line_id`, `order_ref`, `product_id`, `customer_id`, `state`, `created_by` | `qty_ordered`, `qty_delivered`, `price_unit`, `amount` | `date_order`, `date_promised` → `week`, `date_delivered` |
| `fact_purchases` | purchase order line | `line_id`, `order_ref`, `product_id`, `vendor_id`, `state`, `origin`, `created_by` | `qty_ordered`, `qty_received`, `price_unit`, `amount` | `date_order`, `date_planned` (promised) → `week`, `date_received` |
| `fact_production` | manufacturing order | `mo_id`, `mo_ref`, `product_id`, `state`, `origin`, `created_by` | `product_qty`, `qty_produced` | `date_start`, `date_finished` → `week` |
| `fact_stock` | product × internal location (snapshot) | `quant_id`, `product_id`, `location_id`, `location_name` | `quantity`, `reserved_quantity` | snapshot at `meta.extracted_at_utc` |
| `fact_reorder` | reorder rule (snapshot) | `orderpoint_id`, `product_id`, `trigger` | `product_min_qty`, `product_max_qty`, `qty_on_hand`, `qty_forecast`, `qty_to_order` | snapshot |
| `fact_invoices` | posted customer invoice or vendor bill | `move_id`, `move_ref`, `kind` (customer_invoice / vendor_bill / credits), `partner_id`, `payment_state`, `invoice_origin`, `created_by` | `amount_untaxed`, `amount_total`, `amount_residual` (still open) | `invoice_date` → `week`; `invoice_date_due` for aging |
| `fact_payments` | payment | `payment_id`, `payment_ref`, `payment_type` (inbound = from a customer, outbound = to a vendor), `partner_id`, `state` | `amount` | `date` → `week` |
| `fact_stock_moves` | done stock move | `move_id`, `product_id`, `kind` (receipt, delivery, production, consumption, scrap/adjustment, internal), `reference`, `origin` | `quantity`, `on_hand_change` (+ in, − out of the warehouse) | `date` → `week` |
| `fact_forecast` | week (engine) | `week` | `forecast` (the statistical forecast the history was planned on), `demand`, `orders_qty` | `week` |
| `dim_standard_cost` | year × item (engine) | `year`, `item` (product code; `BLG-PWD:material` = its material share) | `std_usd_per_uom` | rolled each January |
| `dim_price_list` | list-price period (engine) | `valid_from` | `list_price` (USD/kg before customer discount), `cost_basis` | reset quarterly |
| `meta` | extraction | `extracted_at_utc`, `database` | `rows_<table>` per table | — |

**Notes**
- `origin` marks special documents: `… at start [mock]` = starting work-in-progress and
  open POs from the demo seed; `RFQ round [mock]` = the sourcing round's draft quotes.
  Filter them out for "planned" volumes.
- Snapshots (`fact_stock`, `fact_reorder`) describe the moment of extraction. **Stock
  over time** is the running sum of `fact_stock_moves.on_hand_change` per product (the
  history starts with an `Opening stock [mock]` receipt on 2023-12-31); value it with
  `dim_standard_cost` for the move's year.
- **KPI recipes:** OTIF = lines whose `date_delivered` (sales) or `date_received`
  (purchases) falls in the promised week, in full; forecast error = `fact_forecast.forecast` vs `orders_qty` (or `demand`); PPV =
  (`fact_purchases.price_unit` − standard) × `qty_received`; AR aging = open
  `fact_invoices` (`amount_residual` > 0, `kind = customer_invoice`) by days past
  `invoice_date_due` at `meta.extracted_at_utc`.
- History documents (ADR 0018) carry `History [mock]` in `origin` / `client_order_ref`;
  emergency buys say so in `origin`. Named events: `outputs/history/events.csv`.
- `fact_forecast`, `dim_standard_cost` and `dim_price_list` come from the engine (`source = engine (mock)`),
  not from Odoo, and only in the live marts.
- Values are mock or derived from cited public data (`knowledge/assumptions.csv`). Any
  published chart built on prices carries the IMF/FRED citation (ADR 0003).
