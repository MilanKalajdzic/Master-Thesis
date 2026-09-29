"""Sample construction: industry reconciliation, exclusions, consistency checks across files, winsorising.

The research choices themselves (which rows are aggregates, which industries are financial, how names are
reconciled) are made in the notebook and passed in.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def is_fin_util(name, keys):
    """True if the industry name contains any of the (lower-case) financial / utility keywords."""
    nl = str(name).lower()
    return any(k in nl for k in keys)


def clean_sample(df, rename, agg_rows, fin_util_keys=None, verbose=True,
                 sum_cols=("n_firms", "mktcap", "div_usd", "ni_usd")):
    """Reconcile names, drop aggregate rows and (if keys are given) financials/utilities, then collapse
    industry-years that the rename map merged: dollar levels and firm counts (`sum_cols`) are summed, ratios
    averaged."""
    df = df.copy()
    df["industry"] = df["industry"].replace(rename)
    df = df[~df["industry"].isin(agg_rows)]
    if fin_util_keys:
        m = df["industry"].apply(lambda n: is_fin_util(n, fin_util_keys))
        if verbose:
            print(f"Excluding {int(m.sum())} financial/utility rows across all years")
        df = df[~m]
    num = [c for c in df.select_dtypes("number").columns if c != "year"]
    agg = {c: ((lambda s: s.sum(min_count=1)) if c in sum_cols else "mean") for c in num}
    df = df.groupby(["industry", "year"], as_index=False).agg(agg)
    return df.reset_index(drop=True)


def winsorize(df, cols, p=0.01):
    """Clip each column at its p and 1-p quantiles (pooled over all years)."""
    df = df.copy()
    for c in cols:
        if c in df:
            lo, hi = df[c].quantile([p, 1 - p]); df[c] = df[c].clip(lo, hi)
    return df


def check_row_alignment(raw, align_vars, min_share, agg_rows):
    """Firm counts of each secondary file (nf_<token> columns) against divfund's `n_firms`, per year.

    An industry has the same number of firms in every file of a year. In a file-year where at least `min_share`
    of the counts match, a row whose count differs belongs to another industry, so that file's variables
    (`align_vars[token]`) are set to missing for it. Where most counts differ, the file covers a different
    vintage of the universe and is left as it is. Returns the corrected frame (without the nf_ columns) and
    one row per file-year describing what was done.
    """
    raw = raw.copy()
    rows = []
    for tok, cols in align_vars.items():
        nf = "nf_" + tok
        if nf not in raw:
            continue
        both = raw["n_firms"].notna() & raw[nf].notna() & ~raw["industry"].isin(agg_rows)
        same = raw["n_firms"] == raw[nf]
        share = same[both].groupby(raw.loc[both, "year"]).mean()
        bad = both & ~same & raw["year"].isin(share[share >= min_share].index)
        raw.loc[bad, [c for c in cols if c in raw]] = np.nan
        for y, s in share.items():
            rows.append({"file": tok, "year": int(y), "share_same_count": round(s, 3),
                         "rows_set_missing": int((bad & (raw["year"] == y)).sum()),
                         "treated_as": "aligned" if s >= min_share else "other vintage (kept)"})
    raw = raw.drop(columns=[c for c in raw if c.startswith("nf_")])
    return raw, pd.DataFrame(rows)


def check_value_agreement(raw, pairs, min_share=0.9, rtol=1e-3, agg_rows=()):
    """Rows whose value disagrees with the same quantity reported in another file, in years where the two
    files otherwise agree exactly.

    `pairs` maps a file to (column, reference column, columns to blank), e.g. wacc's D/(D+E) against dbtfund's
    market debt ratio on the same definition. This catches what the firm-count check cannot: a shifted row whose
    neighbour happens to have the same number of firms. In a year where fewer than `min_share` of the rows agree
    (within relative `rtol`), the files were computed differently and nothing is changed. Run it after
    check_row_alignment (rows already set to missing are skipped). Returns the corrected frame and a table.
    """
    raw = raw.copy()
    rows = []
    for tok, (col, ref, cols) in pairs.items():
        if col not in raw or ref not in raw:
            continue
        both = raw[col].notna() & raw[ref].notna() & ~raw["industry"].isin(agg_rows)
        scale = raw[[col, ref]].abs().max(axis=1).where(lambda s: s > 0, 1.0)
        same = (raw[col] - raw[ref]).abs() / scale < rtol
        share = same[both].groupby(raw.loc[both, "year"]).mean()
        bad = both & ~same & raw["year"].isin(share[share >= min_share].index)
        raw.loc[bad, [c for c in cols if c in raw]] = np.nan
        for y, s in share.items():
            rows.append({"file": tok, "year": int(y), "share_same_value": round(s, 3),
                         "rows_set_missing": int((bad & (raw["year"] == y)).sum()),
                         "treated_as": "same values" if s >= min_share else "computed differently (kept)"})
    return raw, pd.DataFrame(rows)


def crossfile_agreement(raw, rename, industries, tol=0.05):
    """Share of industries per year whose divfund payout ratio equals dividends / net income from divfcfe
    (within `tol`, relative). A year where most disagree points to a scrambled divfcfe file."""
    r = raw[raw["industry"].replace(rename).isin(industries)]
    calc = r["div_usd"] / r["ni_usd"].where(r["ni_usd"] > 0)
    both = r["payout"].gt(0) & calc.notna()
    agree = ((r["payout"] - calc).abs() / calc).lt(tol)
    return agree[both].groupby(r.loc[both, "year"]).mean().rename("share_agree")


def xtsum(df, cols, entity="industry"):
    """Overall / between / within standard deviations (Stata's xtsum)."""
    rows = {}
    for c in cols:
        s = df[[entity, c]].dropna()
        if s.empty:
            continue
        m = s.groupby(entity)[c].transform("mean")
        rows[c] = {"sd_overall": s[c].std(), "sd_between": s.groupby(entity)[c].mean().std(),
                   "sd_within": (s[c] - m + s[c].mean()).std()}
    return pd.DataFrame(rows).T
