import numpy as np
import pandas as pd
import pytest

from paylev import sample
from paylev.synthetic import INDUSTRIES, SHIFTED

AGG = ["Total Market"]


def test_row_alignment_catches_the_shifted_block(raw):
    token, year, a, b = SHIFTED
    fixed, table = sample.check_row_alignment(raw, {"wacc": ["lev", "tax"]}, 0.5, AGG)
    row = table[(table["file"] == "wacc") & (table["year"] == year)].iloc[0]
    assert row["rows_set_missing"] == b - a - 1 and row["treated_as"] == "aligned"   # one has an equal firm count
    assert table.loc[table["year"] != year, "rows_set_missing"].eq(0).all()
    hit = fixed[fixed["year"] == year].set_index("industry")
    caught = [INDUSTRIES[k] for k in range(a, b) if k != a + 2]
    assert hit.loc[caught, "lev"].isna().all() and hit.loc[INDUSTRIES[a + 2], "lev"] == pytest.approx(
        raw.set_index(["year", "industry"]).loc[(year, INDUSTRIES[a + 1]), "lev_unadj"])   # the neighbour's value
    assert not any(c.startswith("nf_") for c in fixed.columns)
    assert raw["lev"].notna().sum() - fixed["lev"].notna().sum() == b - a - 1   # nothing else touched

    fixed2, values = sample.check_value_agreement(fixed, {"wacc": ("lev", "lev_dbt", ["lev", "tax"])}, agg_rows=AGG)
    v = values.set_index("year")
    assert v.loc[year, "rows_set_missing"] == 1 and v.drop(index=year)["rows_set_missing"].eq(0).all()
    assert np.isnan(fixed2.set_index(["year", "industry"]).loc[(year, INDUSTRIES[a + 2]), "lev"])
    assert v["treated_as"].eq("same values").all()


def test_value_check_leaves_differently_computed_years_alone():
    raw = pd.DataFrame({"industry": list("ABCD"), "year": 2001, "lev": [0.10, 0.20, 0.30, 0.40],
                        "lev_dbt": [0.11, 0.21, 0.30, 0.43], "tax": 0.3})
    fixed, table = sample.check_value_agreement(raw, {"wacc": ("lev", "lev_dbt", ["lev", "tax"])})
    assert table.iloc[0]["treated_as"] == "computed differently (kept)" and fixed["lev"].notna().all()


def test_row_alignment_keeps_a_different_vintage():
    raw = pd.DataFrame({"industry": list("ABCD"), "year": 2008, "n_firms": [10, 20, 30, 40],
                        "nf_dbtfund": [11, 21, 31, 41], "lev_book": [0.1, 0.2, 0.3, 0.4]})
    fixed, table = sample.check_row_alignment(raw, {"dbtfund": ["lev_book"]}, 0.5, AGG)
    assert table.iloc[0]["treated_as"] == "other vintage (kept)" and table.iloc[0]["rows_set_missing"] == 0
    assert fixed["lev_book"].notna().all()


def test_crossfile_check_flags_the_year_with_doubled_net_income(raw):
    agree = sample.crossfile_agreement(raw, {}, INDUSTRIES)
    assert agree.loc[2007] < 0.2
    assert agree.drop(2007).eq(1).all()


def test_clean_sample_reconciles_and_excludes():
    df = pd.DataFrame({
        "industry": ["Auto Parts (OEM)", "Auto Parts (Replacement)", "Bank (Regional)", "Total Market", "Steel"],
        "year": 2005, "n_firms": [30, 10, 50, 900, 20], "payout": [0.2, 0.4, 0.5, 0.3, 0.1],
        "mktcap": [300.0, 100.0, 500.0, 9e3, np.nan]})
    out = sample.clean_sample(df, {"Auto Parts (OEM)": "Auto Parts", "Auto Parts (Replacement)": "Auto Parts"},
                              AGG, ["bank"], verbose=False).set_index("industry")
    assert list(out.index) == ["Auto Parts", "Steel"]
    assert out.loc["Auto Parts", "n_firms"] == 40                     # firm counts summed
    assert out.loc["Auto Parts", "mktcap"] == 400                     # dollar levels summed ...
    assert np.isnan(out.loc["Steel", "mktcap"])                       # ... missing stays missing
    assert out.loc["Auto Parts", "payout"] == pytest.approx(0.3)      # ratios averaged
    kept = sample.clean_sample(df, {}, AGG, None, verbose=False)
    assert "Bank (Regional)" in set(kept["industry"])                # no keys: financials kept


def test_is_fin_util():
    keys = ["bank", "utilit", "r.e.i.t"]
    assert sample.is_fin_util("Bank (Midwest)", keys) and sample.is_fin_util("Utility (Water)", keys)
    assert sample.is_fin_util("R.E.I.T.", keys) and not sample.is_fin_util("Steel", keys)


def test_winsorize_clips_at_quantiles():
    df = pd.DataFrame({"x": np.arange(101, dtype=float), "y": np.arange(101, dtype=float)})
    w = sample.winsorize(df, ["x", "missing"], p=0.05)
    assert w["x"].min() == 5 and w["x"].max() == 95 and w["y"].max() == 100


def test_xtsum_splits_between_and_within():
    df = pd.DataFrame({"industry": np.repeat(list("ABC"), 4), "x": np.repeat([1.0, 2.0, 3.0], 4)})
    s = sample.xtsum(df, ["x"]).loc["x"]
    assert s["sd_within"] == 0 and s["sd_between"] == pytest.approx(1.0)
