# 0003: Fetch FRED/IMF price data at runtime; don't commit it

- **Status:** accepted (2026-09-18)
- **Context:** `PMAIZMTUSDM` and `PSUGAISAUSDM` come from the IMF Primary Commodity
  Prices release. FRED marks them as IMF-copyrighted, reprinted with permission, with
  citation required.
- **Decision:** Download via FRED's keyless CSV endpoint into `data/raw/` (gitignored),
  with retrieval metadata. Derived outputs stay in `outputs/` (gitignored). Published
  charts carry the IMF/FRED citation.
- **Alternatives:** commit a snapshot (reproducible, but it's a redistribution question);
  the FRED API (needs a key, which is a secret-handling burden).
- **Consequences:** Runs need the network once, and `--offline` uses the cache. Tests
  use fixtures. FRED stalls custom User-Agents, so the fetcher keeps urllib's default.
