"""Re-download the FRED series used by the thesis and overwrite data/fred/fred_snapshot.csv.

The committed snapshot pins the data vintage so results are exactly reproducible (real GDP is revised
over time). Run this only if you deliberately want a newer vintage, then re-run the notebook. The window matches
the committed snapshot: monthly series from 1998 (for 1999's change in the fed funds rate), GDP from 1997 (for
1998's growth), to the end of the last data year.

Usage:
    python scripts/refresh_fred_snapshot.py [--end 2025-12-31]
"""
import argparse
from pathlib import Path

import pandas as pd

SERIES = ["FEDFUNDS", "GS10", "BAA", "AAA", "GDPC1"]   # monthly, except GDPC1 (quarterly)
OUT = Path(__file__).resolve().parents[1] / "data" / "fred" / "fred_snapshot.csv"


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    """Wide (date x series) frame -> long CSV layout used by the notebook (series_id, date, value)."""
    wide = wide.copy()
    wide.index = pd.to_datetime(wide.index)
    wide.index.name = "date"
    long = wide.reset_index().melt(id_vars="date", var_name="series_id", value_name="value").dropna()
    long["date"] = long["date"].dt.strftime("%Y-%m-%d")
    return long[["series_id", "date", "value"]].sort_values(["series_id", "date"]).reset_index(drop=True)


def main(end="2025-12-31", start_monthly="1998-01-01", start_gdp="1997-01-01"):
    from pandas_datareader import data as pdr
    wide = pdr.DataReader(SERIES, "fred", start_gdp, end)
    long = to_long(wide)
    long = long[(long["series_id"] == "GDPC1") | (long["date"] >= start_monthly)].reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT, index=False)
    print(long.groupby("series_id")["date"].agg(["size", "min", "max"]))
    print(f"-> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--end", default="2025-12-31", help="last date to keep (end of the last data year)")
    main(ap.parse_args().end)
