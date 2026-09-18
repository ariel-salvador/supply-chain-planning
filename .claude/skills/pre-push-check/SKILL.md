---
name: pre-push-check
description: Safety gate before any git push of this (public) repo. Use for "/pre-push-check" and always before proposing or running a push. Runs tests, flags uncited or unlabeled numbers, and scans for emails, phone numbers, API keys, and private deny-list terms.
---

# /pre-push-check

Run the checker and report. **Never push as part of this skill.** Pushing needs the
user's explicit approval in chat, every time.

```bash
.venv/bin/python scripts/pre_push_check.py          # what would be pushed (vs upstream / origin/main)
.venv/bin/python scripts/pre_push_check.py --all    # every tracked file
```

It checks:
1. the test suite
2. `knowledge/assumptions.csv` and every `products/*.yaml`: uncited process numbers,
   raw numbers in configs, rows without a status/source/url/retrieved date, stale
   `used_in`
3. staged and to-be-pushed files **and commit messages** for email, phone and API-key
   patterns (matches are masked)
4. the private deny-list at `$PPS_DENYLIST` (default `~/.config/pps/denylist.txt`)

## Deny-list rules (strict)

- **Never** read, `cat`, `grep`, open, copy, summarize, or reference the deny-list's
  contents. That includes in commands, where they would show up in the transcript. Only
  the script reads it.
- Report deny-list results **only** as the script prints them:
  `N deny-list hits in <file>:<line>`.
- To resolve a hit, open that file and line and ask the user what to change there.
  Don't guess which term matched, and don't echo the line back to the user.
- If the file is missing, the script warns and continues. Pass the warning on.

## Report format

Give the user: tests result, assumptions result, number of findings by kind, the
`file:line` list, and a clear verdict: **clean** or **do not push**. For email or phone
hits in test fixtures, say so. Don't whitelist anything without asking.
