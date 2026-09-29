import shutil

import numpy as np
import pandas as pd
import pytest

from paylev import damodaran as dm
from paylev.synthetic import INDUSTRIES, HEADERS


def test_every_dataset_and_year_is_found(sources):
    for token in dm.TOKENS:
        assert sorted(sources[token]) == list(range(1999, 2026)), token
    assert sources["divfund"][2025].name == "divfund.xlsx"      # the newest file has no year digits


@pytest.mark.parametrize("year", [2004, 2014, 2017, 2019, 2025])   # the three layouts, incl. wacc19's sheet order
def test_reads_the_table_in_every_layout(sources, year):
    for token in dm.TOKENS:
        df = dm.read_industry_sheet(sources[token][year])
        assert df.columns[0] == "industry"
        assert len(df) == len(INDUSTRIES) + 1                    # + the Total Market row
        assert df["industry"].iloc[0] == "Advertising"


def test_year_comes_from_the_stamp_else_from_the_filename(sources, tmp_path):
    assert dm.data_year(sources["wacc"][1999]) == 1999           # no stamp: filename, 99 -> 1999
    assert dm.data_year(sources["wacc"][2005]) == 2005
    assert dm.data_year(sources["divfund"][2025]) == 2025        # no digits: stamp "1/5/2026" -> 2025 data
    wrong = tmp_path / "wacc30.xlsx"
    shutil.copy(sources["wacc"][2021], wrong)
    assert dm.data_year(wrong) == 2021                           # the stamp beats a wrong file name


def test_discover_skips_other_regions_and_lock_files(sources, tmp_path):
    shutil.copy(sources["dbtfund"][2024], tmp_path / "dbtfund24.xlsx")
    shutil.copy(sources["dbtfund"][2023], tmp_path / "dbtfundEurope23.xlsx")
    shutil.copy(sources["dbtfund"][2022], tmp_path / "~$dbtfund22.xlsx")
    found = dm.discover_sources("dbtfund", [tmp_path, tmp_path / "missing"])
    assert list(found) == [2024]


def test_discover_warns_when_two_files_hold_the_same_year(sources, tmp_path):
    shutil.copy(sources["dbtfund"][2024], tmp_path / "dbtfund24.xlsx")
    shutil.copy(sources["dbtfund"][2024], tmp_path / "dbtfund.xlsx")      # e.g. a fresh download of the same year
    with pytest.warns(UserWarning, match="both hold 2024"):
        found = dm.discover_sources("dbtfund", [tmp_path])
    assert list(found) == [2024]


def test_column_pickers_on_real_header_variants():
    fc = pd.DataFrame(columns=["industry", "Number of firms", "  Dividends (US $ millions)", " Net Income (US $ millions)",
                               "Payout", "Dividends + Buybacks(US $ millions)", "Dividend Yield",
                               "FCFE (before debt cash flows)(US $ millions)", "Net Cash Returned/FCFE (pre-debt)"])
    assert dm.pick_div(fc) == "  Dividends (US $ millions)"
    assert dm.pick_fcfe(fc) == "FCFE (before debt cash flows)(US $ millions)"
    assert dm.pick_totpay(fc) == "Dividends + Buybacks(US $ millions)"
    net = pd.DataFrame(columns=["industry", "Dividends + Buybacks - Stock Issuances", "Dividends + Buybacks"])
    assert dm.pick_totpay(net) == "Dividends + Buybacks"                  # gross, not net of issuance
    assert dm.pick_totpay(net[["industry", "Dividends + Buybacks - Stock Issuances"]]) is None
    wc = pd.DataFrame(columns=["industry", "E/(D+E)", "D/(D+E)", "After-tax Cost of Debt", "Tax Rate"])
    assert dm.pick(wc, "d/(d+e)") == "D/(D+E)"                  # not E/(D+E)
    db = pd.DataFrame(columns=["industry", "Book Debt to Capital", "Debt to EBITDA", "EBITDA/EV", "Net PP&E/Total Assets"])
    assert dm.pick(db, "ebitda/") == "EBITDA/EV" and dm.pick(db, "debt", "ebitda") == "Debt to EBITDA"
    assert dm.ppe_column(db) == "Net PP&E/Total Assets"
    assert dm.pick(db, "interest coverage") is None


def test_load_year_reads_the_right_values(sources, fake_dir):
    from paylev.synthetic import _simulate
    sim = _simulate(list(range(1999, 2026)), seed=0)
    for year in [2010, 2016, 2023]:
        r = dm.load_year(year, sources).set_index("industry")
        v = sim[year]["Machinery"]
        assert r.loc["Machinery", "payout"] == pytest.approx(v["payout"])
        assert r.loc["Machinery", "lev"] == pytest.approx(v["lev"])
        assert r.loc["Machinery", "div_yield"] == pytest.approx(v["div"] / v["mktcap"])
        assert r.loc["Machinery", "div_to_fcfe"] == pytest.approx(v["div"] / v["fcfe"])
        assert r.loc["Machinery", "tangibility"] == pytest.approx(v["ppe"])          # PP&E is the default
        assert r.loc["Machinery", "capex_assets"] == pytest.approx(v["capspend"])
        assert r.loc["Machinery", "nf_wacc"] == r.loc["Machinery", "n_firms"]
    assert "totpayout_ni" not in dm.load_year(2010, sources)                  # no buyback column before 2013
    assert "totpayout_ni" not in dm.load_year(2014, sources)                  # 2014-15: only net of issuance
    r16 = dm.load_year(2016, sources).set_index("industry")                   # 2016: both, the gross one is read
    assert r16.loc["Machinery", "totpayout_ni"] == pytest.approx(sim[2016]["Machinery"]["totpay"] / sim[2016]["Machinery"]["ni"])
    r = dm.load_year(2010, sources, tangibility_proxy="capex_deprec").set_index("industry")
    assert r.loc["Machinery", "tangibility"] == pytest.approx(r.loc["Machinery", "capex_deprec"])


def test_non_positive_denominators_give_missing_ratios(sources, tmp_path):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Industry Name", "Number of firms", "  Dividends ", " Net Income ", "FCFE"])
    ws.append(["Steel", 10, 5.0, 20.0, -4.0])        # FCFE < 0
    ws.append(["Machinery", 12, 5.0, 20.0, 10.0])
    wb.save(tmp_path / "divfcfe10.xlsx")
    src = {**sources, "divfcfe": {2010: tmp_path / "divfcfe10.xlsx"}}
    strict = dm.load_year(2010, src).set_index("industry")
    loose = dm.load_year(2010, src, positive_denominators=False).set_index("industry")
    assert np.isnan(strict.loc["Steel", "div_to_fcfe"]) and loose.loc["Steel", "div_to_fcfe"] == pytest.approx(-1.25)
    assert strict.loc["Machinery", "div_to_fcfe"] == pytest.approx(0.5)


def test_tangibility_series(sources):
    t = dm.tangibility_series(sources, "capex_deprec", break_years=[2013, 2014, 2015])
    assert t.loc[t["year"].between(2013, 2015), "t_proxy"].isna().all()
    assert t.loc[~t["year"].between(2013, 2015), "t_proxy"].notna().all()
    p = dm.tangibility_series(sources, "ppe_assets", rename={"Restaurant": "Restaurant/Dining"})
    assert p["t_proxy"].notna().all()
    assert "Restaurant" not in set(p["industry"]) and (p["industry"] == "Restaurant/Dining").sum() == 27
    inv = dm.tangibility_series(sources, "invcap_sales")
    assert inv["t_proxy"].gt(0).all()


def test_headers_cover_every_dataset():
    assert set(HEADERS) == set(dm.TOKENS)
