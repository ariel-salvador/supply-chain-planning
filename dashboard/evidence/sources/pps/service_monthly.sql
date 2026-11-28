-- Customer on-time delivery by promised month, with the likely cause of each miss read
-- from the ERP: ordered less than two weeks ahead (inside the lead time) = rush order;
-- otherwise the shipment itself was held (carrier, quality release).
select date_trunc('month', date_promised) as month,
       customer_name as customer,
       qty_ordered,
       date_trunc('week', date_delivered) <= date_trunc('week', date_promised) as on_time,
       date_diff('day', date_order, date_promised) < 14 as rush,
       case when date_trunc('week', date_delivered) <= date_trunc('week', date_promised) then 'On time'
            when date_diff('day', date_order, date_promised) < 14 then 'Late: rush order'
            else 'Late: shipment held' end as outcome
from fact_sales
where date_delivered is not null
