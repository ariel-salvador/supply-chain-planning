"""Fetch every external dataset into data/raw/ and record where it came from.

Each dataset below documents its source, URL, license and whether derived data may be
committed. Retrieval dates are written next to the cached file
(data/raw/<provider>/<id>.json) and printed.

    .venv/bin/python scripts/fetch_data.py            # fetch if cache older than 7 days
    .venv/bin/python scripts/fetch_data.py --force    # always re-download
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ppsim import fred  # noqa: E402

DATASETS = {
    "PMAIZMTUSDM": {
        "title": "Global price of Corn",
        "units": "U.S. dollars per metric ton, monthly, not seasonally adjusted",
        "provider": "International Monetary Fund, Primary Commodity Prices (via FRED)",
        "url": fred.CSV_URL.format(series="PMAIZMTUSDM"),
        "page": fred.SERIES_URL.format(series="PMAIZMTUSDM"),
        "license": "Copyright IMF; reprinted by FRED with permission; citation required",
        "commit_ok": False,
    },
    "PSUGAISAUSDM": {
        "title": "Global price of Sugar, No. 11, World",
        "units": "U.S. cents per pound, monthly, not seasonally adjusted",
        "provider": "International Monetary Fund, Primary Commodity Prices (via FRED)",
        "url": fred.CSV_URL.format(series="PSUGAISAUSDM"),
        "page": fred.SERIES_URL.format(series="PSUGAISAUSDM"),
        "license": "Copyright IMF; reprinted by FRED with permission; citation required",
        "commit_ok": False,
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / fred.DEFAULT_CACHE)
    args = ap.parse_args()

    ok = True
    for sid, meta in DATASETS.items():
        try:
            s = fred.fetch_series(sid, cache_dir=args.cache_dir, max_age_days=0 if args.force else 7)
            m = fred.cache_metadata(sid, args.cache_dir)
            print(f"{sid:14s} {s.index.min():%Y-%m}..{s.index.max():%Y-%m}  n={len(s):4d}  "
                  f"retrieved {m.get('fetched_at', '?')}  commit_ok={meta['commit_ok']}")
        except fred.FredError as e:
            ok = False
            print(f"{sid:14s} FAILED: {e}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
