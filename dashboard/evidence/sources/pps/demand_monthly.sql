-- Monthly customer demand (orders by promised date) vs the statistical forecast, and
-- what was shipped. Only months fully inside the history (open future orders excluded).
with last_week as (select max(week) as w from fact_forecast),
orders as (
    select date_trunc('month', date_promised) as month,
           sum(qty_ordered) as ordered_kg,
           sum(case when date_delivered is not null then qty_delivered else 0 end) as shipped_kg,
           sum(amount) as order_value_usd
    from fact_sales
    where date_promised < (select w + interval 7 day from last_week)
    group by 1
), forecast as (
    select date_trunc('month', week) as month, sum(forecast) as forecast_kg
    from fact_forecast group by 1
)
select o.month,
       o.ordered_kg,
       f.forecast_kg,
       o.shipped_kg,
       o.order_value_usd,
       (o.ordered_kg - f.forecast_kg) / o.ordered_kg as forecast_error_pct
from orders o join forecast f using (month)
where o.month >= date '2024-01-01'
  and o.month < (select date_trunc('month', w) from last_week)   -- whole months only
order by o.month
