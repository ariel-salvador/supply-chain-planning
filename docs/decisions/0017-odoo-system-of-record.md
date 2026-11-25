# 0017: Odoo is the system of record; scripts are append-only guests in it

- **Status:** accepted (2026-11-24). Phase 0 built and verified the same day.
- **Context:** The user wants to work in Odoo by hand (create purchase orders, receive
  goods, confirm manufacturing orders) **and** have Python generate data (three years
  of history, weekly simulation), with a dashboard reading the result. Until now Odoo
  was disposable: `make odoo-demo` began with `docker compose down -v`, which would
  have deleted any manual work along with the demo.
- **Decision:**
  1. **Two databases in one Odoo instance.** `pps_demo` is disposable and rebuilt by
     `make odoo-demo` (it now drops only that database, never the volumes). `pps_live`
     is the user's system of record.
  2. **Guarded operations** (`scripts/odoo_admin.py`): `drop` refuses `pps_live`
     whatever the flags; `init-live` creates it only if missing; `nuke` (delete every
     volume) refuses without a verified `pps_live` backup younger than 24 h.
  3. **Backups in Odoo's own format:** `odoo db dump` zip (database + filestore),
     verified on write (dump, manifest **and** a non-empty filestore). A restore test
     loads the latest backup into a throwaway database, checks users and filestore
     counts, and drops it.
  4. **Scripts write as `pps-bot`, never as the user.** Operational manager rights only
     (inventory, manufacturing, purchase, sales); no Settings or Access Rights, no
     password (API key only, 90-day expiry, `rpc` scope). Every record shows who made
     it: the user in the UI, or the bot.
  5. **Append-only, idempotent writes.** Each script-created record carries a stable key
     in `x_pps_key`, a manual field added at bootstrap: indexed, and **not copied** when
     a record is duplicated in the UI. `Odoo.ensure()` returns an existing record
     untouched or creates it with the key. It never writes or deletes, so a rerun skips
     what's there and a record the user edited stays as they left it.
  6. **Master-data conflicts:** a sync shows `pending_changes()` (a field-by-field diff)
     and applies nothing without explicit confirmation (decided 2026-11-24).
- **Alternatives:**
  - *Odoo external IDs (`ir.model.data`)* are the native mechanism, but creating them
    needs the "Access Rights" group, which can grant itself anything. Rejected for a
    bot. The admin bootstrap exports the few built-in IDs the bot needs to a local
    `.odoo-live-refs.json` instead.
  - *One database and careful scripts*: one mistake loses the user's work.
  - *Raw `pg_dump` backups*: miss the filestore (attachments) and don't restore
    with `odoo db load`.
- **Consequences:**
  - The browser needs the database in the URL: `127.0.0.1:8069/web/login?db=pps_live`
    (or `?db=pps_demo`). Odoo remembers the choice after login.
  - The bot can't delete contacts (least privilege). Cleanup of bot-made test records
    is by archiving.
  - Verified on 2026-11-24: privilege escalation, editing other users and creating
    users are all denied to the bot; `ensure()` twice gives one record created by the
    bot; backup restores with 441/441 filestore files; a full `make odoo-demo` rebuild
    leaves `pps_live` identical.
  - Two operational gotchas found and fixed while building this: the image's entrypoint
    appends connection flags that `odoo db` rejects (we pass a short-lived config file
    instead, so the password never hits a command line), and that config must set
    `data_dir`, or dumps silently skip the filestore.

## Amendment: master data (2026-11-25)

`scripts/odoo_master.py` (`make odoo-live-master`) loads the config's master data into
`pps_live`: units, partners, products, vendor price lists, BOMs and reorder rules (65
records for case 1). Learned while building it:

- **The bot also needs `product.group_product_manager`** ("Products / Create"): creating
  products and units of measure requires it. It grants no user or settings rights;
  re-verified that the bot still can't escalate.
- **The running server caches each user's groups.** A group added from the bootstrap's
  shell process stays "denied" until Odoo restarts, so the bootstrap now restarts it.
- **Admin-only settings live in the bootstrap**, not the loader: the replenishment
  horizon (182 days = the engine's 26 weeks) and 4-decimal "Product Unit" precision.
- **Reorder rules in `pps_live` use the manual trigger.** With auto, confirming any sales
  order (by hand, or from the history backfill) would immediately create orders. The
  planner runs replenishment instead, and can switch a rule to auto in the UI.
- **Diffs compare to Odoo's stored precision** (half a unit in the 4th decimal), so
  rounding on save isn't reported as an edit.
- Verified: first run creates 65, reruns create 0; a changed reorder minimum is reported
  and left alone, and is reverted only with `APPLY_DIFFS=1`.

## Amendment: the read-only extract (2026-11-25)

`scripts/odoo_extract.py` (`make dashboard-extract`) reads Odoo into marts
(`docs/dashboard/marts.md`). It runs as a third identity, **`pps-reader`**, and is
read-only in two independent layers:

- **Server:** Odoo Community has no read-only role (even "User" levels can create and
  edit), so the bootstrap creates a custom group, *PPS Reader (read-only)*, with read-only
  access rules on the 23 business models the extract needs and no operational groups.
  Verified: creating sales, purchase and manufacturing orders, and editing reorder rules,
  products or contacts are all denied by the server.
- **Client:** `Odoo.reader()` returns a `ReadOnlyOdoo`, which refuses to send anything but
  read methods. The demo extract uses the same client with the demo's key.
- Validated against known numbers: planned powder MOs in the demo extract total
  699,244 kg, matching `docs/odoo/comparison.md` exactly.
