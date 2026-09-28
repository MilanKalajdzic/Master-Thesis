"""FRED macro series: pinned snapshot or live download, annual averages, and the interest-rate regime."""
from __future__ import annotations

import pandas as pd

FRED_SERIES = ["FEDFUNDS", "GS10", "BAA", "AAA", "GDPC1"]   # monthly, except GDPC1 (quarterly)


def load_fred_snapshot(path):
    """The pinned snapshot (long format: series_id, date, value) as a wide date x series frame."""
    s = pd.read_csv(path, parse_dates=["date"])
    return s.pivot(index="date", columns="series_id", values="value")


def fetch_fred_live(start="1998-01-01"):
    from pandas_datareader import data as pdr
    return pdr.DataReader(FRED_SERIES, "fred", start, pd.Timestamp.today())


def annualise(wide):
    """Annual averages of the monthly/quarterly series, plus derived variables."""
    a = wide.resample("YE").mean(); a.index = a.index.year
    out = pd.DataFrame(index=a.index)
    out["ffr"] = a["FEDFUNDS"]                       # annual-average effective fed funds rate
    out["t10"] = a["GS10"]                           # annual-average 10y Treasury yield (monthly GS10)
    out["cred_spread"] = a["BAA"] - a["AAA"]         # Moody's BAA - AAA
    out["gdp_growth"] = a["GDPC1"].pct_change() * 100
    out["ffr_change"] = out["ffr"].diff(); out.index.name = "year"
    return out.reset_index()


def add_regime(m, rule="threshold", threshold=3.0):
    """high_rate = 1 if the annual-average fed funds rate >= threshold ("threshold") or year >= 2022
    ("post2022"); the post-2022 dummy is always kept as high_rate_post2022."""
    m = m.copy()
    m["high_rate"] = ((m["year"] >= 2022).astype(int) if rule == "post2022"
                      else (m["ffr"] >= threshold).astype(int))
    m["high_rate_post2022"] = (m["year"] >= 2022).astype(int)
    return m
