---
name: research
description: Sourced research for this repo. Use for "/research <question>" or whenever a model parameter, process fact, or data source needs finding or verifying. Produces notes, assumptions rows, topic updates, and backlog items, and never leaves findings only in chat.
---

# /research <question>

Goal: answer the question from **public** sources and write everything to files as you go.

1. **Check what exists first** (read the least you need): `docs/status.md` → `INDEX.md` →
   `knowledge/topics/*` → `knowledge/notes/*` → `knowledge/assumptions.csv`. Don't redo
   research that is already recorded.
2. **Find sources.** Prefer peer-reviewed papers (open access where possible), company or
   regulatory pages (FDA GRAS notices, EPA, USDA), and FRED/USDA data. Never use
   anyone's workplace figures, personal info, or paywalled full texts. If a publisher
   blocks scripted downloads, use the in-app browser to read the page.
3. **For each source, write `knowledge/notes/<slug>.md` right away**, using the template
   below. Paraphrase in your own words with section, table or page refs. Quotes must be
   short (under 15 words), with no full-text copying.
4. **For each number the model will use, add or extend a row in
   `knowledge/assumptions.csv`**:
   `id,name,value,unit,low,high,source,url,retrieved,confidence,status,used_in`
   - `status`: `cited` (value stated in a source; `source` includes the locator),
     `estimate` (reasoned from sources; `source` says how), `mock` (illustrative).
   - Leave `low`/`high` blank unless a source gives them. Don't invent ranges.
   - Leave `used_in` blank until a product config references the id.
5. **Update or create a `knowledge/topics/<subject>.md` synthesis** that links the notes.
6. **Add unresolved questions** to `knowledge/backlog.md` (P1/P2/P3).
7. Add new files to `INDEX.md`.
8. Run `.venv/bin/pytest -q` if you touched the CSV. It validates labels and citations.
9. Tell the user in **one line** what you saved (files and ids), then give the answer.

## Note template

```markdown
# <short title>

- **Citation:** Authors (year). Title. Venue vol(issue):pages.
- **URL:** https://doi.org/...  (license if known)
- **Retrieved:** YYYY-MM-DD
- **Reliability:** peer-reviewed / regulatory / industry / preprint, plus caveats (e.g. ex-ante model)
- **reviewed:** false

## Key facts (paraphrased, with locations)
- ... (§2.4)

## Used in
- assumption ids ...

## Open questions
- ...
```
