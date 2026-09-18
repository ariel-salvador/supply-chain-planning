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
- `LICENSE`, `LICENSE-docs`: license texts and scope.

## Knowledge
- `knowledge/assumptions.csv`: every model number with status/source/url. Read before using or adding a number.
- `knowledge/backlog.md`: prioritized open questions. Read when choosing research.
- `knowledge/topics/precision-fermentation-process.md`: Case 1 process train and BOM derivation. Read before touching the BLG config.
- `knowledge/topics/tff-scale-up.md`: MF/UF/DF/drying parameters and DSP capacity gaps. Read for RCCP (M4).
- `knowledge/topics/mrp-concepts.md`: MRP, S&OP and MPS logic as implemented. Read before changing `mrp.py`, `sop.py` or `mps.py`.
- `knowledge/topics/commodity-feedstocks.md`: FRED series, corn→glucose and cents/lb conversions, cost/kg. Read for purchasing (M3).
- `knowledge/notes/behm-2022-rblg-lca.md`: primary Case 1 source (rBLG by *T. reesei*, CC BY).
- `knowledge/notes/humbird-2011-nrel-biochemical-design.md`: NREL *T. reesei* enzyme area: working volume, cycle, seed train, nutrients, uptime.
- `knowledge/notes/odoo-19-community-scope.md`: Odoo 19 Community vs Enterprise modules, JSON-2 API, image pins. Read before Odoo work.
- `knowledge/notes/epa-ap42-corn-wet-milling.md`: corn → starch yield.
- `knowledge/notes/fred-imf-commodity-prices.md`: series, units, license, fetch quirks.
- `knowledge/notes/unit-constants.md`: lb/kg, molar masses.

## Code and data
- `products/blg_whey_protein.yaml`: Case 1 config (structure + assumption ids).
- `src/ppsim/`: engine (see architecture.md for the module map).
- `scripts/fetch_data.py`: dataset provenance and license; fetches into `data/raw/`.
- `scripts/pre_push_check.py`: pre-push gate used by `/pre-push-check`.
- `data/processed/README.md`: what may be committed there.
- `tests/`: offline pytest suite.

## Skills
- `.claude/skills/research/SKILL.md`: `/research <question>`.
- `.claude/skills/log-session/SKILL.md`: `/log-session`.
- `.claude/skills/pre-push-check/SKILL.md`: `/pre-push-check`.
