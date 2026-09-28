"""Re-download the FRED series used by the thesis and overwrite data/fred/fred_snapshot.csv.

The committed snapshot pins the data vintage so results are exactly reproducible (real GDP is revised
over time). Run this only if you deliberately want a newer vintage, then re-run the notebook.

Usage:
    python scripts/refresh_fred_snapshot.py
"""
from pathlib import Path

import pandas as pd

SERIES = ["FEDFUNDS", "GS10", "BAA", "AAA", "GDPC1"]   # monthly, except GDPC1 (quarterly)
OUT = Path("data/fred/fred_snapshot.csv")


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    """Wide (date x series) frame -> long CSV layout used by the notebook (series_id, date, value)."""
    wide = wide.copy()
    wide.index = pd.to_datetime(wide.index)
    wide.index.name = "date"
    long = wide.reset_index().melt(id_vars="date", var_name="series_id", value_name="value").dropna()
    long["date"] = long["date"].dt.strftime("%Y-%m-%d")
    return long[["series_id", "date", "value"]].sort_values(["series_id", "date"]).reset_index(drop=True)


def main(start="1997-01-01", end=None):
    from pandas_datareader import data as pdr
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    wide = pdr.DataReader(SERIES, "fred", start, end)
    long = to_long(wide)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT, index=False)
    print(long.groupby("series_id")["date"].agg(["size", "min", "max"]))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
