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
