# CLAUDE.md

Product-agnostic **production planning simulator**: S&OP → MPS → MRP → purchasing →
rough-cut capacity. Case 1 is a **mock** precision-fermentation plant making
recombinant beta-lactoglobulin (rBLG) whey protein. Feedstock prices are real (FRED),
process parameters are cited, and demand is mock. This repo will be **public**.

## Reading order (read the least you need)

1. `docs/status.md`: handoff. Current milestone, next steps, open questions. **Always first.**
2. `INDEX.md`: map of every doc and note.
3. `knowledge/topics/*`, then `knowledge/notes/*`, then original sources.

## House rules

1. **Every number traces to an id in `knowledge/assumptions.csv`** labeled `cited`,
   `estimate` or `mock`. Product configs reference ids, never raw values. In prose, tag
   numbers [source], [estimate] or [mock]. The loader rejects BOM or price math that
   rests on anything other than `cited` rows.
2. **Save as you go.** Findings go to notes, parameters to `assumptions.csv`, and
   decisions to `docs/decisions/`. Tell the user in one line what you saved.
3. **Public-safe:** no personal info; no employer data or processes (published
   parameters only, never figures from anyone's workplace); no secrets or API keys; no
   copyrighted full texts; check a dataset's license before committing it (FRED/IMF
   series are *not* committable).
4. **Engine ≠ UI.** `src/ppsim/` has no plotting or web imports. Reports read outputs.
   A new product is a new `products/<id>.yaml`, with no product logic in the engine.
5. **Git:** work on branches and commit locally after meaningful changes. **Never push
   or change repo visibility without asking.** Run `/pre-push-check` before any push.
6. Run **`/log-session`** at the end of every work block and before any long task.

## Layout

```
src/ppsim/            engine: registry, config, bom, mrp, demand, fred, feedstock, pipeline, cli
products/<id>.yaml    product configs (structure + assumption ids)
knowledge/            assumptions.csv, notes/, topics/, backlog.md
docs/                 status.md, architecture.md, decisions/
scripts/              fetch_data.py (dataset provenance), pre_push_check.py
data/raw/             download cache (gitignored)   data/processed/  license-permitting only
tests/                pytest, offline
```

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/python scripts/fetch_data.py
.venv/bin/python -m ppsim run products/blg_whey_protein.yaml [--variant sucrose] [--offline]
.venv/bin/python scripts/pre_push_check.py
```

## Skills (`.claude/skills/`)

- `/research <question>`: sourced research → notes, assumptions rows, topics, backlog.
- `/log-session`: update status.md, INDEX.md and backlog, then commit locally.
- `/pre-push-check`: tests, uncited/unlabeled numbers, email/phone/key scan, and a private
  deny-list scan (location-only output; never read or echo the deny-list).

## Conventions

- Python ≥ 3.9: `from __future__ import annotations`; no `match`; no runtime `X | Y`.
- Weekly buckets are pandas Periods; the engine uses integer bucket indices.
- MRP row names follow the textbook. Every planning rule gets a hand-checkable test.
