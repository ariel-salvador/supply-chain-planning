---
sidebar_position: 4
title: Finance
---

```sql margin
select * from pps.margin_quarterly
```

```sql ar
select * from pps.receivables
```

```sql ar_buckets
select bucket, sum(open_usd) as open_usd, count(*) as invoices from ${ar} group by 1 order by 1
```

```sql ar_total
select sum(open_usd) as open_usd, count(*) as invoices,
       sum(case when days_past_due > 0 then open_usd else 0 end) as past_due_usd
from ${ar}
```

```sql margin_ttm
select sum(revenue_usd) as revenue_usd, sum(gross_margin_usd) / sum(revenue_usd) as gm_pct
from (select * from ${margin} order by quarter desc limit 4)
```

```sql price_chart
select quarter, avg_price_usd as avg_price_paid, list_price, std_cost_usd as standard_cost from ${margin}
```

Margin, pricing and cash. Gross margin is at standard cost (materials at the year's
standard plus a fixed conversion cost per kg); price variance sits on the Purchasing page.

<BigValue data={margin_ttm} value=revenue_usd title="Revenue, last 4 quarters" fmt=usd1m />
<BigValue data={margin_ttm} value=gm_pct title="Gross margin, last 4 quarters" fmt=pct1 />
<BigValue data={ar_total} value=open_usd title="Open receivables" fmt=usd0k />
<BigValue data={ar_total} value=past_due_usd title="Past due" fmt=usd0k />

## Is margin holding as prices move?

The list price is reset every quarter from current input costs; key accounts get 3% off
and the distributor 6%. The standard cost is reset each January.

```sql margin_chart
select quarter, gross_margin_usd as gross_margin, gross_margin_pct as margin_pct from ${margin}
```

<BarChart
    data={margin_chart}
    x=quarter
    y=gross_margin
    yFmt=usd1m
    y2=margin_pct
    y2Fmt=pct0
    y2SeriesType=line
    title="Gross margin by quarter"
    colorPalette={['#236aa4', '#e8590c']}
/>

<LineChart
    data={price_chart}
    x=quarter
    y={['list_price', 'avg_price_paid', 'standard_cost']}
    yFmt=usd2
    yMin=8
    title="Price per kg: list, average paid, standard cost"
    colorPalette={['#236aa4', '#45a1bf', '#e8590c']}
/>

Margin stays in a narrow 26-29% band. When input costs rise, the next quarter's list price
follows, so the squeeze lasts at most a quarter.

## Are customers paying on time?

Open invoices at the end of the history, by days past their 30-day due date. Receivables
are healthy: two invoices are a couple of days past due, and nothing is older.

<BarChart
    data={ar_buckets}
    x=bucket
    y=open_usd
    yFmt=usd0k
    title="Receivables by age"
    colorPalette={['#236aa4']}
/>

<DataTable data={ar}>
    <Column id=invoice title="Invoice" />
    <Column id=customer title="Customer" />
    <Column id=invoice_date title="Invoiced" fmt=mmm-d-yyyy />
    <Column id=invoice_date_due title="Due" fmt=mmm-d-yyyy />
    <Column id=open_usd title="Open" fmt=usd0 />
    <Column id=days_past_due title="Days past due" contentType=colorscale />
</DataTable>
