# Status (handoff)

_Last updated: 2026-09-18 · branch `m1-foundation` (local only, not pushed)_

## Current milestone
**M1: FRED pull, mock demand, BOM, basic MRP. Done.** The harness and knowledge base
are in place. Next is M2 (S&OP → MPS) once the P1 research gaps are triaged.

## Done
- Engine `src/ppsim/`: assumptions registry + config loader (process math must rest on
  `cited` ids; planning/demand numbers must be ids; `used_in` checked), BOM (low-level
  codes, explosion), MRP (LFL/FOQ/POQ, min/multiple, safety stock, past-due), FRED CSV
  fetch + cache (`data/raw/`), seeded mock demand, feedstock cost rollup, CLI.
- Case 1 `products/blg_whey_protein.yaml` (glucose base, `sucrose` variant). The M1 run
  gives 0.880 kg rBLG and 4.38 kg sugar per kg powder, and a feedstock-only cost of about
  $1.50/kg (glucose, corn basis) or $1.43/kg (sucrose), at July 2026 FRED prices
  [estimate].
- Knowledge base: 43 rows in `assumptions.csv` (28 cited, 15 mock), 4 notes, 4 topics,
  backlog, 4 ADRs, INDEX.
- Harness: CLAUDE.md, skills `/research`, `/log-session`, `/pre-push-check`
  (`scripts/pre_push_check.py`), `scripts/fetch_data.py`.
- 75 offline tests pass. The pre-push check is clean with `--all`.

## In progress
- Nothing open.

## Next 3 steps
1. `/research` the bioreactor working volume and cycle times (Humbird 2011), which
   unblocks batch sizing.
2. M2: monthly S&OP plan → weekly MPS (time fences, ATP) feeding MRP.
3. First static charts in `reports/` (feedstock cost history with IMF/FRED citation,
   MRP plan).

## Open questions
- License for the repo (TBD).
- Behm yield interpretation (ADR 0004): currently total protein.
- See `knowledge/backlog.md` for the full list.
