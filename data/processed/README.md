# data/processed

Small derived datasets. Only commit them if the upstream license allows it (see
`scripts/fetch_data.py`, field `commit_ok`).

The FRED/IMF commodity series are **not** committable: the IMF holds the copyright and
requires citation. Anything derived from them stays in `outputs/`, which is gitignored.
Published charts must credit: "Source: International Monetary Fund, retrieved from FRED,
Federal Reserve Bank of St. Louis."
