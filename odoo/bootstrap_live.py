# Runs inside `odoo shell -d pps_live` as the superuser (see scripts/odoo_admin.py
# init-live). Idempotent: rerunning only adds what is missing. Prints two lines that
# the caller captures into gitignored files:
#   PPS_BOT_API_KEY=...   -> .odoo-apikey-live
#   PPS_REFS={...}        -> .odoo-live-refs.json
# Secrets never go to the repo. ADR 0017.
import datetime
import json
import os

# --- admin password and fictional company ----------------------------------------
admin = env.ref("base.user_admin")
admin.password = os.environ["ODOO_ADMIN_PASSWORD"]
company = env.company
company.name = os.environ.get("PPS_COMPANY_NAME") or "Demo company (fictional)"
wh = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
if wh:
    wh.name = "Demo Plant (fictional)"

# --- x_pps_key: the stable key of every record a script creates -------------------
# A manual (x_) field, indexed, NOT copied on duplicate, so a record duplicated in the
# UI never inherits a script's key. Only on models the scripts write to.
KEYED_MODELS = [
    "res.partner", "product.template", "product.supplierinfo", "mrp.bom",
    "stock.warehouse.orderpoint", "uom.uom", "sale.order", "purchase.order",
    "mrp.production", "stock.picking", "stock.quant", "account.move", "account.payment",
]
for model in KEYED_MODELS:
    if model not in env:
        continue
    model_rec = env["ir.model"]._get(model)
    if not env["ir.model.fields"].search([("model_id", "=", model_rec.id), ("name", "=", "x_pps_key")]):
        env["ir.model.fields"].create({
            "model_id": model_rec.id,
            "name": "x_pps_key",
            "field_description": "PPS key",
            "ttype": "char",
            "index": True,
            "copied": False,
            "help": "Stable key of a record created by a planning script (ADR 0017). Empty for records created by hand.",
        })

# --- pps-bot: the only identity scripts write as ----------------------------------
# Operational manager rights only: no Settings, no Access Rights, no ability to grant
# itself more. No password, so it can't log into the UI; it authenticates by API key.
BOT_GROUPS = [
    "base.group_user",
    "stock.group_stock_manager",
    "mrp.group_mrp_manager",
    "purchase.group_purchase_manager",
    "sales_team.group_sale_manager",
]
groups = [env.ref(x, raise_if_not_found=False) for x in BOT_GROUPS]
groups = [g.id for g in groups if g]
bot = env["res.users"].with_context(active_test=False).search([("login", "=", "pps-bot")], limit=1)
if not bot:
    bot = env["res.users"].create({
        "name": "PPS Bot (scripts)",
        "login": "pps-bot",
        "group_ids": [(6, 0, groups)],
    })
else:
    bot.write({"active": True, "group_ids": [(6, 0, groups)]})

# a fresh 90-day key on every run; old keys keep working until they expire
expires = datetime.datetime.now() + datetime.timedelta(days=90)
key = env["res.users.apikeys"].with_user(bot).sudo()._generate("rpc", "pps-bot", expires)

# --- xml ids the bot needs but can't resolve itself (no read on ir.model.data) -----
REFS = [
    "uom.product_uom_kgm", "uom.product_uom_unit",
    "mrp.route_warehouse0_manufacture", "purchase_stock.route_warehouse0_buy",
    "stock.warehouse0", "stock.stock_location_stock",
]
refs = {}
for x in REFS:
    rec = env.ref(x, raise_if_not_found=False)
    if rec:
        refs[x] = rec.id

env.cr.commit()
print("PPS_BOT_API_KEY=" + key)
print("PPS_REFS=" + json.dumps(refs, sort_keys=True))
