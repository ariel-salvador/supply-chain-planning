# Status (handoff)

_Last updated: 2026-09-18 · M1 merged to `main` (PR #1); M2 on `m2-sop-mps`, merged via PR #2. Repo is private._

## Current milestone
**M2: S&OP → MPS. Done and merged.** M1 (FRED pull, mock demand, BOM, MRP)
is done, along with the harness, licensing (ADR 0005), and the Humbird research block.

## Done (this block)
- **Research:** Humbird et al. 2011 (NREL): final working volume 80 % (fed-batch from
  50 %), seed-vessel cycle 48 h, uptime 96 %, and the 12,000 kg/batch cross-check. The
  note and 8 cited rows are saved. Fermentation is now planned in whole 12,000 kg batches.
- **M2 engine:** `sop.py` (week↔month split by days, chase/level plan, cover targets on
  daily rate, capacity cap and flags) and `mps.py` (DTF/PTF, capacity-aware catch-up,
  PAB, discrete ATP with look-ahead, mock order book). MRP now accepts the MPS as fixed
  receipts. Config has `time.sop_months`, `demand.orders`, `sop:` and `mps:`.
- **Case 1 run** [mock demand]: the chase plan meets target every month at 58–83 %
  utilization with 3 mock reactors. The MPS stays within capacity, and there are no
  warnings.
- **Records:** ADR 0006 (fermenters as rough-cut constraint), ADR 0007 (S&OP → MPS
  linkage). Topic, architecture and README updated.
- 97 offline tests pass. Registry has 56 rows (36 cited, 20 mock).

## In progress
- Next up (agreed with the user): a visual layer. Start with a static chart report
  (local HTML, no hosting), then maybe a local Streamlit app; hosting decided later.

## Next 3 steps
1. **RCCP (M4) at batch level:** whole-batch rounding gives 4 fermentation starts in
   week 2027-01-11 against 3.36 available. Load batch starts against reactors and
   resolve (level or shift).
2. **M3 purchasing:** planned sugar releases become a PO schedule and spend using FRED
   price history.
3. **First static charts** in `reports/` (S&OP plan, MPS/ATP, feedstock cost with
   IMF/FRED citation).

## Open questions
- DSP throughput and cycle times are still unsourced (backlog P1). Until then DSP is
  assumed unconstrained (ADR 0006).
- Offline time: Behm 24 h (base) vs Humbird 48 h. Uptime of 96 % comes from an ethanol plant.
- See `knowledge/backlog.md`.
