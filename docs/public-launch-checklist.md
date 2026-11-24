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
Checked 2026-11-23: GitHub profile shows **no public email**, and the account has
**0 public repos**, so nothing is exposed yet. All exposure is inside this private repo.

- [x] `scripts/pre_push_check.py` now fails on any commit author/committer that isn't a
      GitHub noreply address (masked output). `--all` currently reports **19** findings:
      the 7 merges + 6 commits × author/committer. It must report 0 before launch.
- [ ] **User:** GitHub → Settings → Emails → enable *Keep my email addresses private*
      and *Block command line pushes that expose my email*. Must happen first, or the
      next `gh pr merge` stamps the personal address again.
- [x] **User:** set the **global** git identity to the noreply address (was the Gmail).
- [ ] **User:** update it again to the renamed account's noreply:
      `git config --global user.email 282146142+ariel-salvador@users.noreply.github.com`
- [ ] Before any of the other private repos ever goes public, run the same
      full-history identity scan on it.
- [x] **User** set the global git identity to the noreply address (2026-11-23).
- [x] **Public GitHub identity decided (2026-11-23):** account renamed to
      `ariel-salvador` (name-based, matches the LinkedIn handle as closely as GitHub
      allowed). Same account ID, so all existing attribution carries over. Repo
      `origin` and local git email updated; license holder updated (ADR 0005 amendment).
      The rewrite maps every identity to `282146142+ariel-salvador@users.noreply.github.com`.
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
- [ ] README section *How this was built*: the AI-assisted workflow (CLAUDE.md,
      skills, ADRs, `Co-Authored-By` trailers), framed as: designed, decided and
      verified by the author; coded with Claude.
- [ ] README opens with three lines: business problem, what was built, result.
- [ ] Dashboard live on GitHub Pages (needs the public repo) with the IMF/FRED
      citation on any derived cost chart (ADR 0003).
