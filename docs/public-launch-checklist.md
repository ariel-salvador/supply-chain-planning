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
- [x] **Dry run passed (2026-11-23)** on a mirror copy: 38 commits in, 38 out; every
      branch tip has an **identical tree hash** (no file content changed); identity scan
      **0**; the re-attributed commits carry a `Co-Authored-By: Claude` trailer. All
      identities become `Ariel Salvador <282146142+ariel-salvador@users.noreply.github.com>`
      except GitHub's own merge committer (`noreply@github.com`, allowed).
      The callback lives **outside the repo** at `~/.config/pps/rewrite_identities.py`
      because it names the old private address. Run it at launch, not before:
      rewriting now would diverge local `main` from the private `origin`.
- [ ] **At launch:** back up (`git bundle create`), run
      `git filter-repo --commit-callback "$(cat ~/.config/pps/rewrite_identities.py)"`,
      re-run `scripts/pre_push_check.py --all` (identity findings must be 0).
- [ ] **User:** set the global git name too: `git config --global user.name "Ariel Salvador"`
      (repo-local name already set).

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
