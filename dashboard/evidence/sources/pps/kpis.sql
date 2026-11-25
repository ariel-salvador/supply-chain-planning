-- Headline KPIs over the trailing 12 months to the end of the history, plus data-as-of.
with last_day as (select max(week) + interval 6 day as d from fact_forecast),
ttm as (select d - interval 365 day as start, d from last_day),
sales as (
    select * from fact_sales, ttm
    where date_delivered is not null and date_delivered > ttm.start and date_delivered <= ttm.d
)
select
    (select sum(amount_untaxed) from fact_invoices, ttm
      where kind = 'customer_invoice' and invoice_date > ttm.start and invoice_date <= ttm.d) as revenue_ttm_usd,
    (select avg(case when date_trunc('week', date_delivered) <= date_trunc('week', date_promised)
                      and qty_delivered >= qty_ordered then 1.0 else 0.0 end) from sales) as otif_ttm,
    (select sum(amount_residual) from fact_invoices
      where kind = 'customer_invoice' and amount_residual > 0) as open_receivables_usd,
    (select cast(left(extracted_at_utc, 10) as date) from meta) as data_as_of,
    (select database from meta) as source_database
