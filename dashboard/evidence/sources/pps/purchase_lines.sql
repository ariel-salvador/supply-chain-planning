-- One row per received purchase-order line: spend, standard cost and price variance
-- (PPV = (paid - standard) x received), delivery performance, supplier status.
select
    p.order_ref,
    p.product_code,
    p.vendor_name                                   as supplier,
    coalesce(d.supplier_status, 'archived')         as supplier_status,
    p.date_order,
    p.date_planned                                  as date_promised,
    p.date_received,
    date_trunc('quarter', p.date_received)          as quarter,
    p.qty_ordered,
    p.qty_received,
    p.price_unit,
    p.qty_received * p.price_unit                   as spend_usd,
    s.std_usd_per_uom                               as std_usd,
    (p.price_unit - s.std_usd_per_uom) * p.qty_received as ppv_usd,
    date_trunc('week', p.date_received) <= date_trunc('week', p.date_planned) as on_time,
    p.qty_received >= p.qty_ordered - 0.001         as in_full,
    p.origin like 'Emergency%'                      as emergency
from fact_purchases p
left join dim_partner d on d.partner_id = p.vendor_id
left join dim_standard_cost s on s.item = p.product_code and s.year = year(p.date_received)
where p.date_received is not null
