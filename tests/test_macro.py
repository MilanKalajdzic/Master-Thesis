import numpy as np
import pandas as pd
import pytest

from paylev.macro import add_regime, annualise, load_fred_snapshot
from paylev.synthetic import HIGH_RATE_YEARS
from tests.conftest import REPO


def test_snapshot_gives_the_three_high_rate_episodes():
    macro = add_regime(annualise(load_fred_snapshot(REPO / "data" / "fred" / "fred_snapshot.csv")))
    m = macro[macro["year"].between(1999, 2025)]
    assert m.loc[m["high_rate"] == 1, "year"].tolist() == HIGH_RATE_YEARS   # the fake data rely on this
    assert m.loc[m["high_rate_post2022"] == 1, "year"].min() == 2022
    assert m[["ffr", "t10", "cred_spread", "gdp_growth", "ffr_change"]].notna().all().all()


def test_annualise_and_regime_rules():
    idx = pd.date_range("2000-01-01", "2002-12-01", freq="MS")
    wide = pd.DataFrame({"FEDFUNDS": np.repeat([6.0, 2.0, 4.0], 12), "GS10": 5.0, "BAA": 8.0, "AAA": 7.0,
                         "GDPC1": np.repeat([100.0, 102.0, 103.02], 12)}, index=idx)
    a = add_regime(annualise(wide), rule="threshold", threshold=3.0).set_index("year")
    assert a["high_rate"].tolist() == [1, 0, 1] and a["cred_spread"].eq(1.0).all()
    assert a.loc[2001, "gdp_growth"] == pytest.approx(2.0) and a.loc[2002, "ffr_change"] == pytest.approx(2.0)
    assert add_regime(annualise(wide), rule="post2022")["high_rate"].eq(0).all()


def test_december_rate_is_the_end_of_year_value():
    idx = pd.date_range("2003-01-01", "2005-12-01", freq="MS")
    ffr = np.r_[np.full(12, 1.2), np.full(6, 1.0), np.linspace(1.25, 2.25, 6), np.linspace(2.5, 4.25, 12)]  # like 2003-05
    wide = pd.DataFrame({"FEDFUNDS": ffr, "GS10": 4.0, "BAA": 6.0, "AAA": 5.0, "GDPC1": 100.0}, index=idx)
    a = annualise(wide).set_index("year")
    assert a.loc[2004, "ffr_dec"] == pytest.approx(2.25) and a.loc[2004, "ffr_change_dec"] == pytest.approx(1.05)
    assert a.loc[2004, "ffr_change"] < 0.25 < a.loc[2004, "ffr_change_dec"]    # hikes from June: missed by the average
    assert np.isnan(a.loc[2003, "ffr_change_dec"])


def test_december_hiking_years_in_the_snapshot():
    macro = annualise(load_fred_snapshot(REPO / "data" / "fred" / "fred_snapshot.csv"))
    m = macro[macro["year"].between(1999, 2025)].set_index("year")
    hike_avg = set(m.index[m["ffr_change"] >= 0.25]); hike_dec = set(m.index[m["ffr_change_dec"] >= 0.25])
    assert {2004} <= hike_dec - hike_avg and {2019} <= hike_avg - hike_dec   # the two cases the README names
