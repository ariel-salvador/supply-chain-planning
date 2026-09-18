# Status (handoff)

_Last updated: 2026-09-18 · branch `m-odoo` (from `main` after the M2 merge; local only, not pushed). Repo is private._

## Current milestone
**ERP: Case 1 in Odoo 19 Community.** It's built and reproducible (`make odoo-demo`,
about 1 min). Screenshots are pending, because they need the user to sign in to the
Odoo UI. M1 and M2 are merged to `main` (PR #1, #2).

## Done (this block)
- **Docker:** OrbStack 2.2.3 installed via Homebrew with the user's OK. The Makefile
  falls back to OrbStack's bundled `docker-compose` if `docker` isn't on PATH.
- **Research (option a, then b):** nutrients cited from Humbird Table 20; 25 kg bags
  from USDA DME1 §2.4. No public source for UF/DF membrane life, so it's a [mock] BOM
  line under ADR 0008 (consumables only).
- **Odoo stack:** `docker-compose.yml` (pinned `odoo:19.0-20260908`,
  `postgres:17.11-bookworm`, localhost only), `.env.example`, `Makefile`,
  `odoo/bootstrap.py`. Secrets are in a gitignored `.env` and `.odoo-apikey`.
- **Scripts:**
  - `odoo_client.py` (JSON-2, since XML-RPC is deprecated)
  - `odoo_seed.py`: fictional company/vendors/customer, batch and lot units, routes,
    BOMs, reorder rules, stock, WIP and open POs, weekly SOs
  - `odoo_run.py`: scheduler run, then export to `data/processed/odoo_plan.csv`
  - `compare_plans.py`: writes `docs/odoo/comparison.md`
- **Finding:** quantities agree to within 7–9 %, and the gap is the engine's S&OP
  inventory build. Odoo's reorder rules replenish the whole 26-week window *now*
  (everything due in weeks 0–1), while the engine time-phases over weeks 1–25.
- **Records:** ADR 0009 (why Odoo Community), `docs/odoo/README.md`, README section
  "Hands-on ERP". Registry has 69 rows. 100 tests pass, and the pre-push check is clean.

## In progress
- Screenshots (BOM, reorder rules, replenishment, MO, RFQ, comparison) for
  `docs/odoo/`. **Blocked:** the user needs to sign in to Odoo in the browser pane
  (I don't enter passwords).

## Next 3 steps
1. Screenshots once the user has signed in. Crop them to the app window, check them
   for usernames, paths and emails, then add them to the README section.
2. Optional Odoo variant: a short horizon plus a rolling daily scheduler, to show how
   Community time-phases.
3. Back to the main track: RCCP at batch level (M4), purchasing (M3), and the static
   chart report (paused; palette already validated).

## Open questions
- Membrane life is still unsourced (ADR 0008). DSP throughput is unsourced (ADR 0006).
- See `knowledge/backlog.md`.
