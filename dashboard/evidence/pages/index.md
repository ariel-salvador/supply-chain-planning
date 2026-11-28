---
title: Supply chain fundamentals
---

<!--
MVP (iteration 1). Reads the read-only marts of the live ERP (pps_live), built by
`make dashboard-extract`. Data dictionary: docs/dashboard/marts.md.
-->

```sql kpis
select * from pps.kpis
```

```sql fg
select * from pps.fg_weekly
```

```sql demand
select * from pps.demand_monthly
```

```sql accuracy
select avg(abs(forecast_error_pct)) as mape,
       avg(forecast_error_pct)      as bias
from ${demand}
```

```sql wos
select week, weeks_of_supply from ${fg} where weeks_of_supply is not null order by week
```

```sql turns
-- finished-goods turns, trailing 52 weeks: kg shipped / average kg on hand
select sum(shipped_kg) / avg(on_hand_kg) as fg_turns,
       avg(weeks_of_supply)              as avg_weeks_of_supply
from (select * from ${fg} order by week desc limit 52)
```

A **mock** precision-fermentation plant making whey protein powder. Three years of
weekly operations recorded in an Odoo ERP. Data as of
**<Value data={kpis} column=data_as_of fmt=longdate />** (ERP database <Value data={kpis} column=source_database />).

<BigValue data={kpis} value=revenue_ttm_usd title="Revenue, last 12 months" fmt=usd1m />
<BigValue data={kpis} value=otif_ttm title="Customer OTIF, last 12 months" fmt=pct1 />
<BigValue data={accuracy} value=mape title="Forecast error (monthly MAPE)" fmt=pct1 />
<BigValue data={turns} value=fg_turns title="Finished-goods turns, last 52 weeks" fmt=num1 />
<BigValue data={wos} value=weeks_of_supply sparkline=week title="Weeks of supply (latest)" fmt=num1 />

## Is supply keeping up with demand?

Customer orders by month against the statistical forecast the plant planned on.
Every order shipped in full and on time, so shipments sit on top of the orders line. Forecast bias: **<Value data={accuracy} column=bias fmt=pct1 />**
(positive = demand above forecast).

```sql demand_chart
select month, ordered_kg as customer_orders, forecast_kg as forecast from ${demand}
```

<LineChart
    data={demand_chart}
    x=month
    y={['customer_orders', 'forecast']}
    colorPalette={['#236aa4', '#e8590c']}
    yFmt=num0
    yAxisTitle="kg of powder"
    title="Monthly customer orders vs forecast"
>
    <ReferenceArea xMin='2026-05-01' xMax='2026-06-30' label="Unforecast launch volume" color=warning/>
</LineChart>

## Is inventory where it should be?

Finished-goods powder on hand at each week's end, against the safety stock set in the
ERP's reorder rule. The weekly saw-tooth is batch production: whole batches of about 13.6 tonnes of powder
arrive, then ship out over the week. Forward weeks of supply (on hand ÷ the next four
weeks' forecast) averaged **<Value data={turns} column=avg_weeks_of_supply fmt=num1 /> weeks**
over the last 52 weeks.

<AreaChart
    data={fg}
    x=week
    y=on_hand_kg
    yFmt=num0
    yAxisTitle="kg on hand"
    title="Finished-goods inventory vs safety stock"
>
    <ReferenceLine data={fg.slice(0, 1)} y=safety_stock_kg label="Safety stock (reorder rule)" color=negative/>
    <ReferenceArea xMin='2025-03-10' xMax='2025-03-23' label="Contaminated batch" color=negative/>
</AreaChart>

---

<small>
Mock company, customers, suppliers and demand (all fictional). Commodity prices behind
costs and revenue are cited: IMF Primary Commodity Prices and US BLS Producer Price
Indices, via FRED (Federal Reserve Bank of St. Louis). Source and method:
github.com/ariel-salvador/supply-chain-planning.
</small>
