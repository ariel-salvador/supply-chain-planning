# Supply chain dashboard (Evidence)

Open-source [Evidence](https://docs.evidence.dev) (`@evidence-dev/evidence` 40.x, pinned):
Markdown + SQL pages, built into a static site. It reads the read-only marts of the live
ERP, `outputs/marts/pps_live/pps.duckdb`, built by `make dashboard-extract`
(`docs/dashboard/marts.md`). No account or hosted warehouse needed.

```bash
make dashboard-extract      # Odoo (pps_live) -> marts, read-only
make evidence-dev           # refresh Evidence's sources from the marts and serve localhost:3000
```

- `sources/pps/*.sql`: the queries Evidence materialises from the marts (weekly
  finished-goods position, monthly demand vs forecast, headline KPIs).
- `pages/index.md`: the page. Iteration 1 (MVP): a KPI row, demand vs forecast,
  finished-goods inventory vs safety stock.

All company, customer, supplier and demand data is mock; commodity prices are cited
(IMF and BLS via FRED) and published charts carry that citation.
