"""Download FRED series as CSV (no API key) with an on-disk cache.

FRED's public graph endpoint returns ``observation_date,<SERIES_ID>`` rows. Missing
observations are written as ``.``. Note: the IMF commodity series used in Case 1 are
copyrighted by the IMF and require citation; keep the cache out of version control.
"""
from __future__ import annotations

import io
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import pandas as pd

CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SERIES_URL = "https://fred.stlouisfed.org/series/{series}"
DEFAULT_CACHE = Path("data/cache/fred")


class FredError(RuntimeError):
    pass


def parse_csv(text: str, series: str) -> pd.Series:
    """Parse FRED graph CSV text into a float Series indexed by date."""
    df = pd.read_csv(io.StringIO(text), na_values=["."])
    date_col = next((c for c in df.columns if c.lower() in ("observation_date", "date")), None)
    if date_col is None or series not in df.columns:
        raise FredError(f"unexpected FRED CSV header for {series}: {list(df.columns)}")
    s = pd.Series(
        pd.to_numeric(df[series], errors="coerce").to_numpy(),
        index=pd.DatetimeIndex(pd.to_datetime(df[date_col]), name="date"),
        name=series,
    )
    return s.dropna()


def _download(series: str, timeout: float, retries: int = 2) -> str:
    url = CSV_URL.format(series=series)
    # Keep urllib's default User-Agent: FRED stalls some custom/browser UAs.
    req = urllib.request.Request(url)
    last: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # network errors, HTTP errors
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise FredError(f"could not download {series} from {url}: {last}")


def fetch_series(
    series: str,
    cache_dir: Union[str, Path] = DEFAULT_CACHE,
    max_age_days: float = 7,
    offline: bool = False,
    timeout: float = 30,
) -> pd.Series:
    """Return a FRED series, using the cache when it is fresh (or when offline)."""
    cache_dir = Path(cache_dir)
    csv_path = cache_dir / f"{series}.csv"
    meta_path = cache_dir / f"{series}.json"

    if csv_path.exists():
        age_days = (time.time() - csv_path.stat().st_mtime) / 86400
        if offline or age_days <= max_age_days:
            return parse_csv(csv_path.read_text(), series)
    elif offline:
        raise FredError(f"{series} is not cached in {cache_dir} and offline mode is on")

    text = _download(series, timeout)
    s = parse_csv(text, series)  # validate before caching
    cache_dir.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(text)
    meta_path.write_text(
        json.dumps(
            {
                "series": series,
                "url": CSV_URL.format(series=series),
                "page": SERIES_URL.format(series=series),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "first": str(s.index.min().date()),
                "last": str(s.index.max().date()),
                "n": int(s.size),
            },
            indent=2,
        )
    )
    return s


def cache_metadata(series: str, cache_dir: Union[str, Path] = DEFAULT_CACHE) -> dict:
    p = Path(cache_dir) / f"{series}.json"
    return json.loads(p.read_text()) if p.exists() else {"series": series}
