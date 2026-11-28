---
sidebar_position: 3
title: Inventory
---

```sql weekly
select * from pps.inventory_weekly
```

```sql by_material
-- trailing 52 weeks: turns = usage / average on hand; weeks of supply = on hand / weekly usage
with last52 as (
    select * from ${weekly}
    where week > (select max(week) from ${weekly}) - interval 52 week
)
select product_code as material, any_value(uom) as uom,
       avg(on_hand)                                  as avg_on_hand,
       sum(used_qty)                                 as used_52w,
       sum(used_qty) / nullif(avg(on_hand), 0)       as turns,
       avg(on_hand) / nullif(avg(used_qty), 0)       as weeks_of_supply,
       avg(value_usd)                                as avg_value_usd
from last52
group by 1
having sum(used_qty) > 0
order by avg_value_usd desc
```

```sql value_weekly
select week,
       case when product_code = 'BLG-PWD' then 'Finished powder'
            when product_code = 'BLG-FERM' then 'Fermented broth (WIP)'
            when product_code = 'GLUCOSE' then 'Glucose'
            else 'Other materials' end as category,
       sum(value_usd) as value_usd
from ${weekly} group by 1, 2 order by 1
```

```sql materials
select distinct product_code from ${weekly}
where kanban_max > 0 and product_code not in ('BLG-PWD') order by 1
```

```sql kanban
select week, on_hand, kanban_min, kanban_max, uom
from ${weekly} where product_code = '${inputs.material.value}' order by week
```

```sql value_now
select sum(value_usd) as value_usd from ${weekly} where week = (select max(week) from ${weekly})
```

How much stock the plant carries, how fast it turns, and whether the new reorder levels
fit. Values at the year's standard cost.

<BigValue data={value_now} value=value_usd title="Inventory value, latest week" fmt=usd0k />

## How fast does each material turn?

Last 52 weeks. Turns = quantity used ÷ average on hand; weeks of supply = average on hand
÷ average weekly use.

<DataTable data={by_material}>
    <Column id=material title="Material" />
    <Column id=uom title="Unit" />
    <Column id=avg_on_hand title="Avg on hand" fmt=num0 />
    <Column id=turns title="Turns / year" fmt=num1 contentType=colorscale />
    <Column id=weeks_of_supply title="Weeks of supply" fmt=num1 />
    <Column id=avg_value_usd title="Avg value" fmt=usd0k />
</DataTable>

Fermentation broth and finished powder turn fastest: each batch moves on within a week or
two. Finished powder still holds the most cash, about two weeks of demand at full cost.
Glucose is next: it's bought in full 250-tonne lots with a 150-tonne safety stock. Membrane
sets turn slowest: one set lasts about 100 batches, so a single spare covers about six
months.

<AreaChart
    data={value_weekly}
    x=week
    y=value_usd
    series=category
    yFmt=usd0k
    title="Inventory value by category"
    colorPalette={['#236aa4', '#45a1bf', '#e8590c', '#8dacbf']}
/>

## Do the kanban reorder levels fit?

In November 2026 every purchased material got a two-bin **kanban**: reorder at the
**min** (usage over the supplier's lead time plus safety stock at a 95% service level),
order up to the **max** (min + one order lot). Odoo's Replenishment screen flags an item
when stock reaches its min. The history below predates the levels, so it shows how
past stock compares with them.

<Dropdown name=material data={materials} value=product_code defaultValue="NH3" title="Material" />

<LineChart
    data={kanban}
    x=week
    y=on_hand
    yFmt=num0
    title="On hand vs kanban levels"
    colorPalette={['#236aa4']}
>
    <ReferenceLine data={kanban.slice(-1)} y=kanban_min label="Reorder at (min)" color=negative/>
    <ReferenceLine data={kanban.slice(-1)} y=kanban_max label="Order up to (max)" color=positive/>
</LineChart>
