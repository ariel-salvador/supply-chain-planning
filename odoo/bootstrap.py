# Runs inside `odoo shell` (see Makefile target odoo-init). Sets the demo admin
# password from the environment and prints a short-lived API key for the seed
# scripts. The key goes to .odoo-apikey (gitignored), never to the repo.
import datetime
import os

admin = env.ref("base.user_admin")
admin.password = os.environ["ODOO_ADMIN_PASSWORD"]
expires = datetime.datetime.now() + datetime.timedelta(days=7)
key = env["res.users.apikeys"].with_user(admin).sudo()._generate(None, "pps-seed", expires)
env.cr.commit()
print("PPS_API_KEY=" + key)
