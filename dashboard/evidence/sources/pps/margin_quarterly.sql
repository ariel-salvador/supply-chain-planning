-- Gross margin by quarter at standard cost: revenue of delivered orders vs kg shipped x
-- the year's standard cost of powder; average price paid vs the list price in force.
with sales as (
    select date_trunc('quarter', date_delivered) as quarter, year(date_delivered) as y,
           sum(qty_delivered) as kg, sum(qty_delivered * price_unit) as revenue_usd
    from fact_sales where date_delivered is not null group by 1, 2
), std as (
    select year, std_usd_per_uom from dim_standard_cost where item = 'BLG-PWD'
), lp as (
    select date_trunc('quarter', valid_from) as quarter, list_price from dim_price_list
)
select s.quarter, s.kg, s.revenue_usd,
       s.kg * std.std_usd_per_uom                            as cogs_std_usd,
       s.revenue_usd - s.kg * std.std_usd_per_uom             as gross_margin_usd,
       1 - s.kg * std.std_usd_per_uom / s.revenue_usd         as gross_margin_pct,
       s.revenue_usd / s.kg                                   as avg_price_usd,
       lp.list_price, std.std_usd_per_uom                     as std_cost_usd
from sales s
join std on std.year = s.y
left join lp using (quarter)
where s.quarter < (select date_trunc('quarter', max(week)) from fact_forecast)   -- whole quarters only
order by s.quarter
