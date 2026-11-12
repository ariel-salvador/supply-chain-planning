# INDEX

One line per doc: what it is, and when to read it. Start with `docs/status.md`.

## Start here
- `docs/status.md`: handoff: milestone, next steps, open questions. **Every session, first.**
- `CLAUDE.md`: purpose, house rules, commands, skills. Read when unsure of a rule.
- `README.md`: public overview and quick start. Read when explaining the project.

## Design
- `docs/architecture.md`: engine / config / UI split, data flow, module map. Read before adding a module.
- `docs/decisions/0001-engine-config-ui-separation.md`: why the engine has no UI or product logic.
- `docs/decisions/0002-assumptions-registry.md`: why every number is a registry id, and what the loader enforces.
- `docs/decisions/0003-fred-data-not-committed.md`: IMF copyright, runtime fetch, citation on charts.
- `docs/decisions/0004-blg-yield-interpretation.md`: 0.223 g/g read as total protein (conservative).
- `docs/decisions/0005-licensing.md`: MIT for code, CC BY 4.0 for docs/ and knowledge/; holder is the GitHub handle.
- `docs/decisions/0006-fermenters-as-rough-cut-constraint.md`: capacity basis for S&OP/MPS; DSP assumed unconstrained until sourced.
- `docs/decisions/0007-sop-to-mps-linkage.md`: month/week split, cover targets, time fences, catch-up, MPS → MRP.
- `docs/decisions/0008-mock-quantities-for-consumables.md`: [mock] BOM lines allowed only for consumables (membranes).
- `docs/decisions/0009-odoo-community-scope.md`: why Odoo Community; S&OP/MPS/capacity stay in Python (verified limits).
- `docs/decisions/0010-rccp-bill-of-resources-and-leveling.md`: RCCP load in release week; pull-forward leveling.
- `docs/decisions/0011-purchasing-spend-scenarios.md`: PO schedule; spend only from public price series; p10/p50/p90.
- `docs/decisions/0012-supplier-master.md`: supplier master vs the Odoo vendor list; archetypes; award drives the POs.
- `docs/decisions/0013-rfq-scoring-and-award.md`: range-normalised weighted scoring, written rationale, mock quotes as a should-cost index.
- `docs/decisions/0014-should-cost-build-up.md`: should-cost = material + conversion + margin; TCO adds landed, MOQ and quality cost.
- `docs/decisions/0015-supplier-performance-and-risk.md`: simulated delivery history, PPV, exposure-based single vs dual source.
- `docs/decisions/0016-odoo-sourcing-mirror.md`: multi-vendor price lists and draft RFQs in Odoo Community (unverified).
- `docs/odoo/README.md`: Odoo demo: run it, config→Odoo mapping, screens, lessons.
- `docs/odoo/comparison.md`: generated Odoo vs engine plan comparison.
- `LICENSE`, `LICENSE-docs`: license texts and scope.

## Knowledge
- `knowledge/assumptions.csv`: every model number with status/source/url. Read before using or adding a number.
- `knowledge/backlog.md`: prioritized open questions. Read when choosing research.
- `knowledge/topics/precision-fermentation-process.md`: Case 1 process train and BOM derivation. Read before touching the BLG config.
- `knowledge/topics/tff-scale-up.md`: MF/UF/DF/drying parameters and DSP capacity gaps. Read for RCCP (M4).
- `knowledge/topics/mrp-concepts.md`: MRP, S&OP, MPS and RCCP logic as implemented. Read before changing `mrp.py`, `sop.py`, `mps.py` or `rccp.py`.
- `knowledge/topics/sourcing-concepts.md`: should-cost, RFQ scoring, TCO and incoterms, OTIF/PPV, single vs dual source, as implemented. Read before changing `sourcing.py` or `supplier_perf.py`.
- `knowledge/topics/commodity-feedstocks.md`: FRED series, corn→glucose and cents/lb conversions, cost/kg. Read for purchasing (M3).
- `knowledge/notes/behm-2022-rblg-lca.md`: primary Case 1 source (rBLG by *T. reesei*, CC BY).
- `knowledge/notes/humbird-2011-nrel-biochemical-design.md`: NREL *T. reesei* enzyme area: working volume, cycle, seed train, nutrients, uptime.
- `knowledge/notes/odoo-19-community-scope.md`: Odoo 19 Community vs Enterprise modules, JSON-2 API, image pins. Read before Odoo work.
- `knowledge/notes/usda-dme1-dairy-powder-packaging.md`: 25 kg multiwall bag spec (analog dairy powder).
- `knowledge/notes/epa-ap42-corn-wet-milling.md`: corn → starch yield.
- `knowledge/notes/fred-imf-commodity-prices.md`: series, units, license, fetch quirks.
- `knowledge/notes/unit-constants.md`: lb/kg, molar masses.

## Code and data
- `products/blg_whey_protein.yaml`: Case 1 config (structure + assumption ids).
- `src/ppsim/`: engine (see architecture.md for the module map).
- `scripts/fetch_data.py`: dataset provenance and license; fetches into `data/raw/`.
- `scripts/pre_push_check.py`: pre-push gate used by `/pre-push-check`.
- `scripts/odoo_client.py`, `odoo_seed.py`, `odoo_run.py`, `odoo_sourcing.py`, `compare_plans.py`: Odoo JSON-2 demo (`make odoo-demo`). `odoo_sourcing.py` runs last on purpose (ADR 0016).
- `docker-compose.yml`, `Makefile`, `.env.example`, `odoo/bootstrap.py`: local Odoo stack.
- `reports/build_report.py`, `reports/template.html`: static chart report (`make report`).
- `data/processed/README.md`: what may be committed there.
- `tests/`: offline pytest suite.

## Skills
- `.claude/skills/research/SKILL.md`: `/research <question>`.
- `.claude/skills/log-session/SKILL.md`: `/log-session`.
- `.claude/skills/pre-push-check/SKILL.md`: `/pre-push-check`.
