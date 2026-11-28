---
sidebar_position: 2
title: Purchasing
---

```sql lines
select * from pps.purchase_lines
```

```sql by_supplier
select supplier, supplier_status,
       sum(spend_usd)                         as spend_usd,
       count(distinct order_ref)              as orders,
       avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       avg(case when in_full then 1.0 else 0 end) as in_full_pct,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct,
       sum(ppv_usd)                           as ppv_usd
from ${lines} group by 1, 2 order by spend_usd desc
```

```sql totals
select sum(spend_usd) as spend_usd,
       sum(case when supplier_status = 'preferred' then spend_usd else 0 end) / sum(spend_usd) as preferred_share,
       sum(ppv_usd) as ppv_usd,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct
from ${lines}
```

```sql ppv_quarter
select quarter,
       case when product_code = 'GLUCOSE' then 'Glucose (corn index)'
            when product_code in ('NH3', 'AMSULF') then 'Nitrogen chemicals'
            else 'Other materials' end as material_group,
       sum(ppv_usd) as ppv_usd
from ${lines} group by 1, 2 order by 1
```

```sql outage
-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from ${lines}
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from ${lines} where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order
```

```sql outage_total
select sum(premium_usd) as premium_usd, sum(qty_received) as kg from ${outage}
```

What the plant buys, from whom, and how prices and suppliers performed. Seven
suppliers: four **preferred** partners that win the business by default, and three
**approved** backups.

<BigValue data={totals} value=spend_usd title="Spend, Jan 2024 to Nov 2026" fmt=usd1m />
<BigValue data={totals} value=preferred_share title="Spend with preferred partners" fmt=pct1 />
<BigValue data={totals} value=ppv_usd title="Price variance vs standard" fmt=usd0k />
<BigValue data={totals} value=otif_pct title="Supplier on time and in full" fmt=pct1 />

## Who do we buy from, and do they deliver?

<DataTable data={by_supplier} rows=10>
    <Column id=supplier title="Supplier" />
    <Column id=supplier_status title="Status" />
    <Column id=spend_usd title="Spend" fmt=usd0k />
    <Column id=orders title="Orders" />
    <Column id=on_time_pct title="On time" fmt=pct0 contentType=colorscale />
    <Column id=in_full_pct title="In full" fmt=pct0 contentType=colorscale />
    <Column id=ppv_usd title="Price variance" fmt=usd0k />
</DataTable>

The glucose mill carries most of the spend and misses about one delivery in ten. The
packaging converter is the cheapest bag supplier but the least reliable (about four in
five on time, some short shipments). The chemicals distributor costs more and is never
late. That trade-off is why it is the preferred partner rather than the cheaper broadline
distributor.

## Are we paying more or less than planned?

Purchase price variance = (price paid − standard cost) × quantity received. Standard costs
are set each January from December's market prices, so variance shows how markets moved
during the year. Above zero = paid more than planned.

<BarChart
    data={ppv_quarter}
    x=quarter
    y=ppv_usd
    series=material_group
    type=stacked
    yFmt=usd0k
    title="Purchase price variance by quarter"
    colorPalette={['#236aa4', '#e8590c', '#8dacbf']}
/>

In 2024 corn fell after the standard was set, so glucose came in under plan. In 2026
nitrogen chemicals rose all year with the fertilizer market (US producer price index),
and variance turned unfavorable.

## What did the August 2025 glucose outage cost?

The preferred mill could not deliver for four weeks. Production never stopped: the buyer
placed emergency orders with the backup supplier, who delivered in a week at a premium.

<BigValue data={outage_total} value=premium_usd title="Premium paid to the backup" fmt=usd0k />
<BigValue data={outage_total} value=kg title="Glucose bought in the outage (kg)" fmt=num0 />

<DataTable data={outage}>
    <Column id=order_ref title="PO" />
    <Column id=supplier title="Supplier" />
    <Column id=date_order title="Ordered" fmt=mmm-d-yyyy />
    <Column id=qty_received title="kg" fmt=num0 />
    <Column id=price_unit title="Paid $/kg" fmt='$0.000' />
    <Column id=preferred_price title="Mill's last $/kg" fmt='$0.000' />
    <Column id=premium_usd title="Premium" fmt=usd0 />
</DataTable>

Against the yearly standard these orders even look favorable, because corn had fallen
below the January standard. The real cost of the outage is the premium over what the
preferred mill was charging at the time.
