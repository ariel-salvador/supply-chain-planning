# Status (handoff)

_Last updated: 2026-09-18_

**Branch:** `m1-foundation` (local only, not pushed)
**Milestone:** M1 done: FRED pull, mock demand, BOM, basic MRP.

## Done
- Engine `src/ppsim/`: config loader (rejects process parameters without citations),
  safe expression evaluator, BOM (low-level codes, explosion), MRP (LFL/FOQ/POQ,
  min/multiple, safety stock, past-due), FRED CSV fetch and cache, seeded mock demand,
  feedstock cost rollup, CLI.
- Case 1 config `products/blg_whey_protein/` (base = glucose, variant `sucrose`).
- 45 offline tests passing.
- Research saved in `knowledge/notes/` (Behm 2022, EPA AP-42, FRED/IMF, constants).

## Next 3 steps
1. Source the bioreactor working volume (start with Humbird et al. 2011, NREL/TP-5100-47764)
   → batch lot sizing.
2. M2: monthly S&OP plan → weekly MPS (time fences, ATP).
3. M5-lite: first static charts (feedstock cost history, MRP plan) in `reports/`.

## Open questions
- Behm yield 0.223 g/g: total protein or rBLG only? (Currently treated as total, the
  conservative reading.)
- Harness restructure requested by the other session (skills, assumptions.csv, ADRs):
  waiting on the user's decisions.
