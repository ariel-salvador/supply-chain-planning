# Status (handoff)

_Last updated: 2026-09-18 · branch `m4-rccp` (from `main` after PR #3; contains M4, M3 and M5; local only, not pushed). Repo is private._

## Current milestone
**All planned milestones are built:** M1–M5, plus the Odoo ERP demo. M1, M2 and the
Odoo work are merged to `main` (PR #1–#3). M4 (RCCP), M3 (purchasing) and M5 (static
report) are on `m4-rccp`, waiting for review and push.

## Done (this block)
- **M4 RCCP** (`rccp.py`, ADR 0010): a bill of resources in config (fermenter hours per
  kg rBLG = cited 144 h ÷ 12,000 kg), load placed in the release week, and pull-forward
  leveling (≤ 2 weeks [mock]) that re-runs MRP. Peak fermenter load goes from 119 % to
  89 %, with one batch moved from week 1 to week 0.
- **M3 purchasing** (`purchasing.py`, ADR 0011): one PO per vendor per release week.
  Spend is priced from FRED-linked prices with p10/p50/p90 over 10 years [mock
  window]. Glucose over 26 weeks: about $0.94M base, $0.67–1.30M range [estimate].
  Nutrients, bags and membranes are excluded, not guessed.
- **M5 static report** (`reports/`, `make report`): a self-contained HTML page with 4
  KPI tiles and 8 charts (S&OP, MPS with fences, PAB, fermenter load before/after,
  glucose purchasing, spend scenarios, feedstock cost since 1992). Colors are
  validated for colorblind safety; it has tooltips, table views and light/dark mode.
  It's local only (IMF data).
- **Also:** the `days_per_week` registry row's `used_in` was fixed. 111 tests pass, and
  the pre-push check is clean.

## In progress
- Nothing open. Waiting for the user's review of `m4-rccp`.

## Next 3 steps
1. With the user's OK: pre-push check, push `m4-rccp`, PR #4, merge.
2. Public-facing report variant: publish charts with mock/cited data plus derived cost
   (with IMF citation), without the raw price series. Decide the hosting (GitHub Pages?)
   with the user first.
3. Research: DSP throughput (UF/DF flux, dryer capacity), then add DSP lines to the
   bill of resources; public price series for NH₃ and salts.

## Open questions
- Membrane life (ADR 0008) and DSP throughput (ADR 0006) are still unsourced.
- See `knowledge/backlog.md`.
