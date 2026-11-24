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
