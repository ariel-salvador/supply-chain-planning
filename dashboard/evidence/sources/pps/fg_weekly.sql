-- Finished-goods (powder) position per week: on hand at week end (running sum of every
-- done stock move, starting from the opening count), shipped, and forward weeks of supply
-- (on hand / average forecast of the next 4 weeks). Safety stock = the Odoo reorder rule.
with fg as (
    select product_id from dim_product where product_code = 'BLG-PWD'
), moves as (
    select date_trunc('week', date) as week,
           sum(on_hand_change) as change_kg,
           sum(case when kind = 'delivery' then quantity else 0 end) as shipped_kg,
           sum(case when kind = 'production' then quantity else 0 end) as produced_kg
    from fact_stock_moves
    where product_id = (select product_id from fg)
    group by 1
), weeks as (
    select week from fact_forecast
    union
    select week from moves
), position as (
    select w.week,
           coalesce(m.shipped_kg, 0) as shipped_kg,
           coalesce(m.produced_kg, 0) as produced_kg,
           sum(coalesce(m.change_kg, 0)) over (order by w.week) as on_hand_kg
    from weeks w left join moves m using (week)
)
select p.week,
       p.on_hand_kg,
       p.shipped_kg,
       p.produced_kg,
       f.forecast as forecast_kg,
       p.on_hand_kg / nullif(avg(f.forecast) over (order by p.week rows between 1 following and 4 following), 0)
           as weeks_of_supply,
       (select product_min_qty from fact_reorder r
         join dim_product d on d.product_id = r.product_id where d.product_code = 'BLG-PWD') as safety_stock_kg
from position p
join fact_forecast f using (week)
order by p.week
