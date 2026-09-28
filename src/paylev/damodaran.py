"""Damodaran (NYU Stern) US industry files: locate, read and combine them.

The files come in three layouts: 1999-2012 (`Sheet1`, no date stamp), 2013-2018 (`Sheet1` with a "Date updated"
stamp) and 2019+ (`Variables & FAQ` + `Industry Averages`). Columns are renamed from year to year, so they are
matched by keyword rather than by exact name.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

TOKENS = ["divfund", "divfcfe", "wacc", "capex", "dbtfund"]
CAPEX_PROXIES = {"capex_deprec", "netcapex_sales", "invcap_sales"}   # tangibility proxies read from `capex`
DEPREC_PROXIES = {"capex_deprec", "netcapex_sales"}                  # ... that depend on depreciation


def read_industry_sheet(path, scan=45):
    """Locate and read the industry table across all Damodaran layouts (1999-2025)."""
    xl = pd.ExcelFile(path)
    named = [s for s in xl.sheet_names if "industry" in s.lower()]
    for sh in named + [s for s in xl.sheet_names if s not in named]:
        raw = pd.read_excel(path, sheet_name=sh, header=None, nrows=scan)
        if raw.empty:
            continue
        for i in range(len(raw)):
            if str(raw.iloc[i, 0]).strip().lower().startswith("industry"):
                df = pd.read_excel(path, sheet_name=sh, header=i).dropna(how="all")
                df = df.rename(columns={df.columns[0]: "industry"})
                df["industry"] = df["industry"].astype(str).str.strip()
                return df[df["industry"].str.lower() != "nan"].copy()
    raise ValueError(f"No industry table found in {path}")


def pick(df, *keys):
    """First column whose name contains every keyword (case-insensitive), or None."""
    keys = [k.lower() for k in keys]
    for c in df.columns:
        if all(k in str(c).lower() for k in keys):
            return c
    return None


def pick_fcfe(df):
    """FCFE level column (not a ratio): starts with 'fcfe', no '/'. Prefers 'before debt'."""
    for c in df.columns:
        cl = str(c).lower().strip()
        if cl.startswith("fcfe") and "/" not in str(c):
            return c
    return None


def pick_div(df):
    """Dividend level column ($), excluding ratios, buybacks, payout, yield."""
    for c in df.columns:
        cl = str(c).lower()
        if "dividend" in cl and "/" not in str(c) and not any(
                e in cl for e in ["yield", "buyback", "net income", "payout"]):
            return c
    return None


def nfirms(df):
    """Number-of-firms column as numbers (NaN if the file has none), for the row-alignment check."""
    c = pick(df, "number", "firm")
    return pd.to_numeric(df[c], errors="coerce") if c else np.nan


def data_year(path):
    """Data year: internal 'Date updated' stamp (year-1) if present, else filename (Y2K pivot)."""
    try:
        xl = pd.ExcelFile(path)
        for sh in xl.sheet_names:
            raw = pd.read_excel(path, sheet_name=sh, header=None, nrows=6)
            for i in range(len(raw)):
                if "date updated" in str(raw.iloc[i, 0]).lower():
                    return pd.to_datetime(raw.iloc[i, 1]).year - 1
    except Exception:
        pass
    m = re.search(r"(\d{2,4})(?=\D*$)", Path(path).stem)
    if m:
        n = int(m.group(1))
        return n if n >= 100 else (1900 + n if n >= 50 else 2000 + n)
    return None


def discover_sources(token, search_dirs):
    """{data year: file} for one dataset, searching `search_dirs` recursively (absent paths are ignored)."""
    found = {}
    for d in search_dirs:
        d = Path(d)
        if not d.exists():
            continue
        for f in sorted(d.rglob(f"{token}*.xls*")):
            # token + optional year digits only (so e.g. dbtfundEurope24.xls is not read as dbtfund)
            if f.name.startswith("~$") or not re.fullmatch(rf"{token}\d*\.xlsx?", f.name, re.I):
                continue
            y = data_year(f)
            if y is not None:
                found.setdefault(y, f)
    return found


def capex_tangibility(cx, proxy):
    """A capex-based tangibility proxy from one capex table (see CAPEX_PROXIES)."""
    if proxy == "netcapex_sales":
        c = pick(cx, "net cap ex", "sales") or pick(cx, "cap ex", "sales")
    elif proxy == "invcap_sales":
        c = pick(cx, "sales", "capital") or pick(cx, "sales", "invested")
        if c is None:                          # column absent in older capex files
            return pd.Series(np.nan, index=cx.index)
        return 1.0 / pd.to_numeric(cx[c], errors="coerce").replace(0, np.nan)
    else:
        c = pick(cx, "cap ex", "deprec")       # capex_deprec (present every year)
    if c is None:
        return pd.Series(np.nan, index=cx.index)
    return pd.to_numeric(cx[c], errors="coerce")


def ppe_column(db):
    """PP&E / assets column of a dbtfund table (named three ways over the years)."""
    return pick(db, "fixed assets/") or pick(db, "pp&e/")


def load_year(year, sources, tangibility_proxy="ppe_assets", positive_denominators=True):
    """One year's industry rows, merged across the five files by industry name (raw names, before reconciliation).

    `sources` maps each token to {year: path}; divfund and wacc are required, the others are merged when present.
    Firm counts of the secondary files are kept as nf_<token> for the row-alignment check.
    """
    dv = read_industry_sheet(sources["divfund"][year])
    wc = read_industry_sheet(sources["wacc"][year])
    out = pd.DataFrame({"industry": dv["industry"], "year": year})
    out["payout"] = pd.to_numeric(dv[pick(dv, "dividend", "payout")], errors="coerce")
    out["roe"]    = pd.to_numeric(dv[pick(dv, "roe")], errors="coerce")
    nf = pick(dv, "number", "firm")
    out["n_firms"] = pd.to_numeric(dv[nf], errors="coerce") if nf else np.nan   # weights (§9)
    mc = pick(dv, "market cap")
    out["mktcap"] = pd.to_numeric(dv[mc], errors="coerce") if mc else np.nan
    out = out.merge(pd.DataFrame({
        "industry": wc["industry"],
        "lev": pd.to_numeric(wc[pick(wc, "d/(d+e)")], errors="coerce"),
        "tax": pd.to_numeric(wc[pick(wc, "tax")], errors="coerce"),
        "nf_wacc": nfirms(wc),                     # row-alignment check (§2)
    }), on="industry", how="left")
    if year in sources.get("divfcfe", {}):
        fc = read_industry_sheet(sources["divfcfe"][year])
        dcol, fcol = pick_div(fc), pick_fcfe(fc)
        tot, ni = pick(fc, "dividends", "buyback"), pick(fc, "net income")
        f = pd.DataFrame({"industry": fc["industry"], "nf_divfcfe": nfirms(fc)})
        if dcol:
            f["div_usd"] = pd.to_numeric(fc[dcol], errors="coerce")   # $m, used for checks and §8b
        if ni:
            f["ni_usd"] = pd.to_numeric(fc[ni], errors="coerce")

        def _den(col):                                  # denominator; <= 0 -> undefined ratio
            s = pd.to_numeric(fc[col], errors="coerce")
            return s.where(s > 0) if positive_denominators else s.replace(0, np.nan)
        if dcol and fcol:
            f["div_to_fcfe"] = pd.to_numeric(fc[dcol], errors="coerce") / _den(fcol)
        if tot and ni:
            f["totpayout_ni"] = pd.to_numeric(fc[tot], errors="coerce") / _den(ni)
        out = out.merge(f, on="industry", how="left")
        if "div_usd" in out:                        # earnings-free payout measure (§9 ROE check)
            out["div_yield"] = out["div_usd"] / out["mktcap"].where(out["mktcap"] > 0)
    if year in sources.get("capex", {}):
        cx = read_industry_sheet(sources["capex"][year])
        g = pd.DataFrame({"industry": cx["industry"], "nf_capex": nfirms(cx),
                          "capex_deprec": pd.to_numeric(cx[pick(cx, "cap ex", "deprec")], errors="coerce")})
        if tangibility_proxy in CAPEX_PROXIES:
            g["tangibility"] = capex_tangibility(cx, tangibility_proxy)
        out = out.merge(g, on="industry", how="left")
    if year in sources.get("dbtfund", {}):
        db = read_industry_sheet(sources["dbtfund"][year])
        num = lambda c: pd.to_numeric(db[c], errors="coerce") if c else np.nan   # noqa: E731
        g = pd.DataFrame({
            "industry": db["industry"], "nf_dbtfund": nfirms(db),
            # market D/(D+E) without the lease adjustment (wacc's D/(D+E) includes leases from 2013 on)
            "lev_unadj": num(pick(db, "mv debt ratio") or pick(db, "market debt to capital", "unadjusted")),
            "lev_book": num(pick(db, "bv debt ratio") or pick(db, "book debt to capital")),
            "ebitda_ev": num(pick(db, "ebitda/")),                       # EBITDA / firm value (every year)
            "ppe_assets": num(ppe_column(db)),
            "capex_assets": num(pick(db, "capital spending")),              # reinvestment: capex / capital or assets
            "debt_ebitda_rep": num(pick(db, "debt", "ebitda")),           # reported only 2018, 2022+
            "int_cov": num(pick(db, "interest coverage")),                # reported only 2022+
        })
        if tangibility_proxy == "ppe_assets":
            g["tangibility"] = g["ppe_assets"]
        out = out.merge(g, on="industry", how="left")
    return out


def tangibility_series(sources, proxy, rename=None, break_years=()):
    """Every year's value of one tangibility measure, with the same industry reconciliation as the main panel.

    Industries merged by `rename` are averaged; depreciation-based proxies are missing in `break_years`.
    (PP&E is returned as a level; the analysis ranks it within each year.)
    """
    fr = []
    if proxy == "ppe_assets":
        for y in sorted(sources["dbtfund"]):
            db = read_industry_sheet(sources["dbtfund"][y])
            fr.append(pd.DataFrame({"industry": db["industry"], "year": y,
                                    "t_proxy": pd.to_numeric(db[ppe_column(db)], errors="coerce")}))
    else:
        for y in sorted(sources["capex"]):
            cx = read_industry_sheet(sources["capex"][y])
            fr.append(pd.DataFrame({"industry": cx["industry"], "year": y,
                                    "t_proxy": capex_tangibility(cx, proxy)}))
    t = pd.concat(fr, ignore_index=True)
    t["industry"] = t["industry"].replace(rename or {})
    t = t.groupby(["industry", "year"], as_index=False)["t_proxy"].mean()
    if proxy in DEPREC_PROXIES:
        t.loc[t["year"].isin(list(break_years)), "t_proxy"] = np.nan
    return t
