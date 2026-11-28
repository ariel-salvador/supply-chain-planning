-- Open customer invoices at the end of the history, aged by days past due.
with history_end as (select max(week) + interval 6 day as d from fact_forecast)
select i.move_ref as invoice, i.partner_name as customer, i.invoice_date, i.invoice_date_due,
       i.amount_total, i.amount_residual as open_usd,
       date_diff('day', i.invoice_date_due, (select d from history_end)) as days_past_due,
       case when date_diff('day', i.invoice_date_due, (select d from history_end)) <= 0 then '1. Not yet due'
            when date_diff('day', i.invoice_date_due, (select d from history_end)) <= 30 then '2. 1-30 days'
            when date_diff('day', i.invoice_date_due, (select d from history_end)) <= 60 then '3. 31-60 days'
            when date_diff('day', i.invoice_date_due, (select d from history_end)) <= 90 then '4. 61-90 days'
            else '5. 90+ days' end as bucket
from fact_invoices i
where i.kind = 'customer_invoice' and i.amount_residual > 0.005
order by days_past_due desc
