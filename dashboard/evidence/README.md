# Supply chain dashboard (Evidence)

Open-source [Evidence](https://docs.evidence.dev) (`@evidence-dev/evidence` 40.x, pinned):
Markdown + SQL pages, built into a static site. It reads the read-only marts of the live
ERP, `outputs/marts/pps_live/pps.duckdb`, built by `make dashboard-extract`
(`docs/dashboard/marts.md`). No account or hosted warehouse needed.

```bash
make dashboard-extract      # Odoo (pps_live) -> marts, read-only
make evidence-dev           # refresh Evidence's sources from the marts and serve localhost:3000
make evidence-publish       # refresh, build, scan and push to GitHub Pages (gh-pages branch)
```

Published at https://ariel-salvador.github.io/supply-chain-planning/ (`deployment.basePath`
in `evidence.config.yaml`; set it to `""` if the site moves to its own subdomain). The ERP
is local, so the site is built here and only the build is pushed. `scripts/publish_evidence.py`
scans every built text file first (emails, phone numbers, keys, the private deny-list) and
stops on any finding; `--dry-run` lists what would go public.

- `sources/pps/*.sql`: the queries Evidence materialises from the marts (weekly
  finished-goods position, monthly demand vs forecast, headline KPIs).
- `pages/index.md`: the page. Iteration 1 (MVP): a KPI row, demand vs forecast,
  finished-goods inventory vs safety stock.

All company, customer, supplier and demand data is mock; commodity prices are cited
(IMF and BLS via FRED) and published charts carry that citation.
