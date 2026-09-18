---
name: log-session
description: End-of-work-block handoff. Use for "/log-session", at the end of every work block, and before any long-running task. Updates docs/status.md, INDEX.md and knowledge/backlog.md, then commits locally.
---

# /log-session

Make the repo the source of truth so a fresh session can resume from `docs/status.md`.

1. **Update `docs/status.md`** (keep it under ~60 lines):
   - `Last updated: YYYY-MM-DD` and the current branch
   - Current milestone
   - Done (this block, concise), In progress, **Next 3 steps**, Open questions
   - Anything decided in chat that isn't in a file yet: write it here or add an ADR in
     `docs/decisions/NNNN-title.md` (context, decision, alternatives, consequences).
2. **Update `INDEX.md`**: one line per doc or note (what it is, when to read it). Add new
   files and remove deleted ones.
3. **Update `knowledge/backlog.md`**: add new questions, strike resolved ones (note where
   they were resolved), and re-prioritize.
4. **Check that findings from this block are in files** (notes, `assumptions.csv`, topics),
   not only in chat.
5. Run `.venv/bin/pytest -q`. If it fails, record that in status.md. Don't hide it.
6. **Commit locally** on the current branch (never `main` directly, **never push**):
   `git add -A && git commit -m "log: <one-line summary>"` with the repo's attribution
   trailer.
7. Tell the user in one line what was updated and the commit hash.
