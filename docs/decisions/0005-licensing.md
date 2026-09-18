# 0005: MIT for code, CC BY 4.0 for docs and research content

- **Status:** accepted (2026-09-18), decided by the repo owner.
- **Context:** The repo will be public as a portfolio project. Without a license,
  others would have no right to reuse anything. The research write-ups (`docs/`,
  `knowledge/`) are the most distinctive part, and the main source (Behm et al. 2022)
  is itself CC BY.
- **Decision:** Code, configs, tests and scripts use MIT (`LICENSE`). `docs/` and
  `knowledge/` use CC BY 4.0 (`LICENSE-docs`), so reusers must credit the project.
  The copyright holder is the GitHub handle `agenttofu0`, not a legal name
  (no-personal-info rule).
- **Alternatives:** MIT for everything (simplest, but credit is weaker for prose);
  Apache-2.0 (adds a patent grant that isn't needed here); no license (all rights
  reserved, which blocks reuse).
- **Consequences:** Two license files, with scope stated in both and in the README.
  Third-party papers and data are explicitly excluded. IMF/FRED data stays uncommitted
  (ADR 0003). New top-level content directories must be assigned to one license.
