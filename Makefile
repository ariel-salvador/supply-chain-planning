# Odoo Community (local only). Two databases in one instance (ADR 0017):
#   pps_demo  disposable: `make odoo-demo` rebuilds it from scratch
#   pps_live  the user's system of record: never dropped by any target here
SHELL := /bin/bash
PY    := .venv/bin/python
XBIN  := /Applications/OrbStack.app/Contents/MacOS/xbin

# Prefer `docker compose` on PATH; fall back to OrbStack's bundled binary.
ifeq ($(shell docker compose version >/dev/null 2>&1 && echo ok),ok)
  COMPOSE := docker compose
else
  COMPOSE := $(XBIN)/docker-compose
  export DOCKER_HOST ?= unix://$(HOME)/.orbstack/run/docker.sock
  export PATH := $(XBIN):$(PATH)
endif

-include .env
export
DB ?= $(ODOO_DB_NAME)
APPS := stock,mrp,purchase,sale_management

.PHONY: report odoo-env odoo-up odoo-init odoo-seed odoo-run odoo-compare odoo-rfq odoo-demo odoo-demo-reset odoo-down odoo-logs \
        odoo-live-init odoo-live-bootstrap odoo-live-master odoo-backup odoo-restore-test odoo-nuke

report:              ## build outputs/report/index.html (static charts, local only)
	$(PY) reports/build_report.py products/blg_whey_protein.yaml

odoo-env:            ## create .env with random secrets if missing (never printed)
	@test -f .env || $(PY) -c "import secrets,re; s=open('.env.example').read(); \
s=re.sub(r'change-me-db-password', secrets.token_urlsafe(24), s); \
s=re.sub(r'change-me-admin-password', secrets.token_urlsafe(18), s); \
open('.env','w').write(s)" && chmod 600 .env && echo ".env ready (gitignored)"

odoo-up: odoo-env    ## start Postgres + Odoo on 127.0.0.1:8069
	$(COMPOSE) up -d
	@for i in $$(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:8069/web/login && break || sleep 2; done; echo "odoo up"

odoo-init:           ## create the demo DB, install apps, set admin password, write API key
	$(COMPOSE) run --rm odoo odoo -d $(DB) -i $(APPS) --stop-after-init --no-http
	@$(COMPOSE) run --rm -T -e ODOO_ADMIN_PASSWORD odoo odoo shell -d $(DB) --no-http < odoo/bootstrap.py 2>/dev/null \
	  | sed -n 's/^PPS_API_KEY=//p' > .odoo-apikey && chmod 600 .odoo-apikey && test -s .odoo-apikey && echo "API key written to .odoo-apikey"
	$(COMPOSE) restart odoo

odoo-seed:           ## load products/blg_whey_protein.yaml into Odoo via JSON-2
	$(PY) scripts/odoo_seed.py products/blg_whey_protein.yaml

odoo-run:            ## run the scheduler and export MOs / POs
	$(PY) scripts/odoo_run.py

odoo-compare:        ## diff Odoo's plan against the Python MRP
	$(PY) scripts/compare_plans.py products/blg_whey_protein.yaml

odoo-rfq:            ## create the RFQ round (run AFTER odoo-run: drafts count as supply in progress)
	$(PY) scripts/odoo_sourcing.py products/blg_whey_protein.yaml

odoo-demo: odoo-up odoo-demo-reset odoo-init odoo-seed odoo-run odoo-compare odoo-rfq  ## rebuild pps_demo only

odoo-demo-reset:     ## drop pps_demo (database + filestore). Volumes and pps_live are untouched
	$(PY) scripts/odoo_admin.py drop $(ODOO_DB_NAME) --if-exists

odoo-down:
	$(COMPOSE) down

odoo-live-init:      ## create pps_live (only if missing): apps, pps-bot user, API key
	$(PY) scripts/odoo_admin.py init-live

odoo-live-bootstrap: ## re-run the pps_live bootstrap (idempotent; issues a fresh bot key)
	$(PY) scripts/odoo_admin.py bootstrap-live

odoo-live-master:    ## load master data into pps_live (append-only; shows diffs, APPLY_DIFFS=1 to write them)
	$(PY) scripts/odoo_master.py products/blg_whey_protein.yaml $(if $(APPLY_DIFFS),--apply-diffs,)

odoo-backup:         ## verified backup (db + filestore zip) -> backups/  (BACKUP_DB=pps_demo for the demo)
	$(PY) scripts/odoo_admin.py backup $(or $(BACKUP_DB),$(ODOO_LIVE_DB_NAME),pps_live)

odoo-restore-test:   ## prove the latest pps_live backup restores (into a throwaway DB, then dropped)
	$(PY) scripts/odoo_admin.py restore-test $(or $(BACKUP_DB),$(ODOO_LIVE_DB_NAME),pps_live)

odoo-nuke:           ## DELETE EVERY VOLUME incl. pps_live; refuses without a fresh pps_live backup
	$(PY) scripts/odoo_admin.py nuke --i-understand-this-deletes-pps-live

odoo-logs:
	$(COMPOSE) logs --tail=100 odoo
