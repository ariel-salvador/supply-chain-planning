# Runs inside `odoo shell -d pps_live` as the superuser (see scripts/odoo_admin.py
# init-live). Idempotent: rerunning only adds what is missing. Prints two lines that
# the caller captures into gitignored files:
#   PPS_BOT_API_KEY=...   -> .odoo-apikey-live
#   PPS_READER_API_KEY=... -> .odoo-apikey-reader
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

# --- settings that need admin rights (the bot deliberately has none) --------------
# replenishment look-ahead = the engine's planning horizon, so both see the same window
if os.environ.get("PPS_HORIZON_DAYS"):
    company.horizon_days = float(os.environ["PPS_HORIZON_DAYS"])
# 4 decimals so per-batch BOM quantities (e.g. 0.01 membrane set) don't round to zero
prec = env["decimal.precision"].search([("name", "=", "Product Unit")], limit=1)
if prec and prec.digits < 4:
    prec.digits = 4

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
    "product.group_product_manager",   # "Products / Create": products and units of measure
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

# --- pps-reader: read-only identity for the dashboard extract ---------------------
# A custom group with READ-ONLY access to the business models the extract pulls. The
# user is internal (so it can hold an API key and read internal documents) but gets no
# operational groups, so it can't create or edit orders, stock, products or BOMs.
READ_MODELS = [
    "res.partner", "res.company", "res.currency", "uom.uom", "product.category",
    "product.template", "product.product", "product.supplierinfo", "mrp.bom", "mrp.bom.line",
    "mrp.production", "stock.warehouse", "stock.location", "stock.quant", "stock.move",
    "stock.picking", "stock.warehouse.orderpoint", "sale.order", "sale.order.line",
    "purchase.order", "purchase.order.line", "account.move", "account.move.line",
]
reader_group = env["res.groups"].search([("name", "=", "PPS Reader (read-only)")], limit=1)
if not reader_group:
    reader_group = env["res.groups"].create({"name": "PPS Reader (read-only)"})
for model in READ_MODELS:
    if model not in env:
        continue
    acl_name = f"pps_reader_{model.replace('.', '_')}"
    if not env["ir.model.access"].search([("name", "=", acl_name)]):
        env["ir.model.access"].create({
            "name": acl_name, "model_id": env["ir.model"]._get(model).id, "group_id": reader_group.id,
            "perm_read": True, "perm_write": False, "perm_create": False, "perm_unlink": False,
        })
reader_groups = [env.ref("base.group_user").id, reader_group.id]
reader = env["res.users"].with_context(active_test=False).search([("login", "=", "pps-reader")], limit=1)
if not reader:
    reader = env["res.users"].create({
        "name": "PPS Reader (dashboard extract)", "login": "pps-reader",
        "group_ids": [(6, 0, reader_groups)],
    })
else:
    reader.write({"active": True, "group_ids": [(6, 0, reader_groups)]})
reader_key = env["res.users.apikeys"].with_user(reader).sudo()._generate("rpc", "pps-reader", expires)

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
print("PPS_READER_API_KEY=" + reader_key)
print("PPS_REFS=" + json.dumps(refs, sort_keys=True))
