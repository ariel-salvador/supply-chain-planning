---
sidebar_position: 1
title: Customer service
---

```sql orders
select * from pps.service_monthly
```

```sql monthly
select month, outcome, count(*) as orders from ${orders} group by 1, 2 order by 1
```

```sql otif_month
select month, avg(case when on_time then 1.0 else 0 end) as on_time_pct from ${orders} group by 1 order by 1
```

```sql by_customer
select customer, count(*) as orders,
       avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       sum(case when outcome = 'Late: rush order' then 1 else 0 end) as late_rush,
       sum(case when outcome = 'Late: shipment held' then 1 else 0 end) as late_held,
       avg(case when rush then 1.0 else 0 end) as rush_share
from ${orders} group by 1 order by on_time_pct
```

```sql totals
select avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       sum(case when not on_time then 1 else 0 end) as late_orders,
       avg(case when rush then 1.0 else 0 end) as rush_share
from ${orders}
```

Did customers get their orders in the week they were promised? Every order ships whole,
so "in full" always holds and on-time is the measure.

<BigValue data={totals} value=on_time_pct title="On time, all orders" fmt=pct1 />
<BigValue data={totals} value=late_orders title="Late orders" />
<BigValue data={totals} value=rush_share title="Orders placed inside lead time" fmt=pct0 />

## When did we miss, and why?

Odoo doesn't record a reason, so the cause is read from the order itself. An order placed
less than two weeks before its promised date came in inside the lead time (a **rush
order**). Any other late order was ready but **held** (carrier no-show, quality release).

<BarChart
    data={monthly}
    x=month
    y=orders
    series=outcome
    type=stacked
    title="Orders by promised month and outcome"
    colorPalette={['#8dacbf', '#e8590c', '#c2410c']}
/>

<LineChart
    data={otif_month}
    x=month
    y=on_time_pct
    yFmt=pct0
    yMin=0.6
    title="On-time rate by month"
    colorPalette={['#236aa4']}
>
    <ReferenceLine y=0.95 label="95% target" color=warning/>
</LineChart>

Most misses are held shipments, not shortages: there was product, and it left a week late.
Rush orders rarely miss because finished-goods stock (about two weeks of demand) absorbs
them. The March 2025 contamination cost no orders for the same reason; see the Home page
inventory chart.

## By customer

<DataTable data={by_customer}>
    <Column id=customer title="Customer" />
    <Column id=orders title="Orders" />
    <Column id=on_time_pct title="On time" fmt=pct1 contentType=colorscale />
    <Column id=rush_share title="Rush share" fmt=pct0 />
    <Column id=late_rush title="Late: rush" />
    <Column id=late_held title="Late: held" />
</DataTable>
