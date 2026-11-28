-- On hand per product at each week's end (running sum of done stock moves from the
-- opening count), weekly usage (consumed by production, or shipped for powder), value at
-- the year's standard cost, and the kanban min/max now set on the ERP reorder rule.
with mv as (
    select product_id, date_trunc('week', date) as week,
           sum(on_hand_change) as change_qty,
           sum(case when kind in ('consumption', 'delivery') then quantity else 0 end) as used_qty
    from fact_stock_moves group by 1, 2
), weeks as (
    select week from fact_forecast union select week from mv
), grid as (
    select p.product_id, p.product_code, p.uom_name, w.week from dim_product p cross join weeks w
), pos as (
    select g.product_id, g.product_code, g.uom_name, g.week,
           coalesce(m.used_qty, 0) as used_qty,
           sum(coalesce(m.change_qty, 0)) over (partition by g.product_id order by g.week) as on_hand
    from grid g left join mv m using (product_id, week)
)
select pos.product_code, pos.uom_name as uom, pos.week, pos.on_hand, pos.used_qty,
       pos.on_hand * s.std_usd_per_uom as value_usd,
       r.product_min_qty as kanban_min, r.product_max_qty as kanban_max
from pos
left join fact_reorder r using (product_id)
left join dim_standard_cost s on s.item = pos.product_code and s.year = year(pos.week)
where pos.week >= (select min(week) from fact_forecast)
order by pos.product_code, pos.week
