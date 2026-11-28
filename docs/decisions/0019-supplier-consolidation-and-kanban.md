# 0019: Consolidated supplier master, buyable minimums, kanban reorder levels

- **Status:** accepted (2026-11-27, reviewed and approved by the user before it was applied).
- **Context:** The M6 supplier master had three bidders per material family (incumbent,
  low-cost, premium): 12 suppliers, each selling one family. Real buyers consolidate:
  one distributor covers many items. Working in Odoo also showed two problems:
  minimum order quantities such as 0.0423 membrane sets (the MOQ was "N weeks of usage",
  never rounded to something buyable), and reorder rules of min = max = 0 for every input
  except glucose, so Replenishment never flagged them.
- **Decision:**
  1. **Seven suppliers, named for what they sell**: four *preferred* partners (Corn
     Sweeteners Mill, Process Chemicals Distributor, Packaging Converter, Filtration
     Systems Maker) and three *approved* backups that each cover several families
     (Broadline Ingredients Distributor, Regional Express Supply, Aftermarket Membrane
     Supply). Every item keeps at least two bids; each has exactly one preferred partner,
     and the RFQ scoring still awards every item to it (tested).
  2. **Status and traits are data, not name text**: `status` and `tags` in the config
     become Odoo contact tags (*Preferred supplier* / *Approved supplier*, *Low cost*,
     *Fast delivery*, *Import*, ...). Names describe the business and stay true when an
     award changes. The per-item default is the price-list order (sequence 1), as before.
  3. **Generic role names drop the "(fictional)" suffix** (the user's call). They are
     still flagged `fictional: true`, which the loader requires. Customer and company
     names keep the suffix for now: "Precision Proteins" is a real business line of a
     real company, so the company needs a new invented name before its suffix goes.
  4. **Minimums are buyable**: rounded up to a whole shipping lot where one is set (25 t
     tanker, pallet of 1,000 bags: mock), else whole units / whole kg. Membrane sets: 1.
  5. **Kanban (two-bin) reorder levels** for purchased items, from the awarded supplier:
     safety stock = z·√(L·(cv·d)² + d²·σL²) (cited 95% z), never below the plan's own;
     min = d·L + safety stock; max = min + one order lot (the minimum or fixed lot). Odoo's
     Replenishment then shows when to reorder and how much.
  6. **The history stays reproducible.** The new *express* quote profile prices at the
     premium index (1.09), so the outage's emergency buys from the backup reproduce to
     the cent, and the migration re-keys history documents to the new supplier ids.
- **Migration of the live ERP** (`scripts/odoo_migrate_suppliers.py`, dry run first): for
  each new supplier one old record is renamed and re-keyed in place, so its three years
  of purchase orders, receipts, bills and payments follow it; the other five are
  archived. Price-list lines move to their new supplier. **The two lines of retired
  suppliers are deleted**: Odoo price-list lines can't be archived, and this one-off,
  approved migration is the only exception to "scripts never delete". Contact tags are
  created by the admin bootstrap (the bot has no right to create tags, only to attach them).
- **Verified (2026-11-27):** rehearsed on a copy of `pps_live`, then applied after a
  backup (`pps_live-20261128T013936Z.zip`): 7 renames, 5 archives, 22 lines moved, 2
  deleted, 333 history documents re-keyed; 37 master-data differences applied; reruns of
  both find nothing; `check_history.py` passes everything (stock, dates, revenue and
  spend to the cent).
- **Consequences:**
  - ADR 0016's MOQ finding changes shape in the demo. Weekly bag orders (393–1,630) are
    still below the preferred converter's 7,000 minimum (the engine still flags it), but
    the backup's minimum (2,000) doesn't fit either, so Odoo now falls back to the
    preferred vendor instead of splitting to a runner-up. In the live system the kanban
    order lot (7,000) meets the minimum, which is the real fix: lot size and award are
    one decision.
  - The extract's `dim_partner` gains `supplier_status`, `tags` and `active` (archived
    suppliers stay, so old documents still join).
