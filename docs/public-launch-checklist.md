# Public launch checklist

_Created 2026-11-23. Nothing here is done yet. Going public is effectively
irreversible (forks, clones and caches persist), so every item is done **before** the
visibility change._

## Audit result (2026-11-23)

Full-history scan of every version of every file (237 text blobs) and all 34 commit
messages, using `scripts/pre_push_check.py` scanners plus the private deny-list:
**0** emails, phone numbers or API keys; **0** deny-list hits. `.env`, `.odoo-apikey`
and raw FRED/IMF data were never committed. The only problems are in commit
**identity metadata**, not file contents.

## Checklist

### Identity (blocking)
- [ ] **User:** GitHub → Settings → Emails → enable *Keep my email addresses private*
      and *Block command line pushes that expose my email*. Must happen first, or the
      next `gh pr merge` stamps the personal address again.
- [ ] Rewrite history locally: the 7 PR merge commits (#1–#7) carry the personal email
      as author → replace with the GitHub noreply address.
- [ ] Re-attribute the 6 commits authored as `noreply@anthropic.com` (742930c,
      a0128cb, c00e667, 77388d6, 4999ce0, 4a603ed) to the user, keeping a Claude
      `Co-Authored-By` trailer.
- [ ] Show the before/after identity list for review before touching GitHub.

### Publishing (blocking, needs the user's OK)
- [ ] Rename the current repo to `production-planning-simulator-archive`; keep it
      **private** (closed PR pages there still link to the old merge commits).
- [ ] Create a fresh public repo with the original name; push the rewritten history.
      Full commit history is kept; PR pages are not.
- [ ] Re-run the full-history scan on the new repo before announcing it.

### Presentation
- [ ] Clean `docs/status.md` (drop stale "next steps").
- [ ] README opens with three lines: business problem, what was built, result.
- [ ] State AI use plainly: designed and verified by the author, coded with AI.
- [ ] Dashboard live on GitHub Pages (needs the public repo) with the IMF/FRED
      citation on any derived cost chart (ADR 0003).
