"""Draw the README figures (docs/img/*.png, a light and a dark version of each) from the notebook's outputs.

    python scripts/run_notebook.py      # first: writes outputs/, including analysis_panel.csv
    python scripts/readme_figures.py

    python scripts/readme_figures.py --outputs <dir> --data <dir> --img <dir>   # other locations (the tests)

The figures re-estimate a few models from outputs/analysis_panel.csv with the same estimator as the notebook
(year-by-year leverage slopes, the H3 marginal effect) and read everything else from the result tables. The
data-quality figure reads the raw Damodaran files for the file-year the row-alignment check flagged.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
try:
    import paylev  # noqa: F401
except ImportError:                                   # package not installed: use the copy in src/
    sys.path.insert(0, str(REPO / "src"))
from paylev.damodaran import TOKENS, discover_sources, load_year  # noqa: E402
from paylev.estimation import fit_panel, lincom  # noqa: E402
from paylev.plotting import THEMES, dot, minus, runs, save, shade, titles, use  # noqa: E402

CONTROLS = ["roe", "tax", "size"]
H3_REGS = ["lev", "tangibility", "lev_x_high", "lev_x_tang", "high_x_tang", "lev_x_high_x_tang"]
EQUIV_MARGIN = 0.05

# ---------------------------------------------------------------------------------------------------------------
def hero(t, panel, path):
    """Fed funds rate with the three high-rate episodes, and the payout-on-leverage slope for every year."""
    years = sorted(panel["year"].unique())
    d = panel.copy()
    for y in years:
        d[f"lev_{y}"] = d["lev"] * (d["year"] == y)
    names = [f"lev_{y}" for y in years]
    r = fit_panel(d, "payout", names + CONTROLS, verbose=False)
    b, se = r.params[names].to_numpy(), r.std_errors[names].to_numpy()
    ri = fit_panel(panel, "payout", ["lev", "lev_x_high"] + CONTROLS, verbose=False)
    low, high = ri.params["lev"], lincom(ri, {"lev": 1, "lev_x_high": 1})[0]
    rate = panel.groupby("year")[["ffr", "high_rate"]].first().reindex(years)
    hi = rate["high_rate"].eq(1).to_numpy()

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True, gridspec_kw={"height_ratios": [1, 2.3]})
    fig.subplots_adjust(left=0.075, right=0.80, top=0.835, bottom=0.13, hspace=0.12)
    titles(fig, t, "Three rate cycles, one payout–leverage slope",
           "Top: fed funds rate (annual average); high-rate years (≥ 3%) shaded.  Bottom: payout-on-leverage slope "
           "estimated for each year, 95% CI,\nindustry and year effects, controls ROE, tax, size. If H2 held, the "
           "shaded years would sit lower.")
    episodes = runs(years, hi)
    for ax in (a1, a2):
        shade(ax, episodes, t)
    a1.plot(years, rate["ffr"], color=t["ink2"], lw=2)
    a1.axhline(3, color=t["base"], lw=1)
    a1.text(years[-1] + .7, 3, "3%", color=t["muted"], va="center", fontsize=9)
    a1.set_ylabel("Fed funds, %")
    for run in episodes:
        lab = f"{run[0]}–{str(run[-1])[2:]}" if len(run) > 1 else str(run[0])
        a1.text((run[0] + run[-1]) / 2, rate["ffr"].max() * 1.02, lab, ha="center", va="bottom", fontsize=9,
                color=t["ink2"])
    a1.set_ylim(0, rate["ffr"].max() * 1.25)

    a2.axhline(0, color=t["base"], lw=1, zorder=1)
    for x, bb, ss, h in zip(years, b, se, hi):
        c = t["s2"] if h else t["s1"]
        a2.plot([x, x], [bb - 1.96 * ss, bb + 1.96 * ss], color=c, lw=1.4, alpha=t["whisker"], zorder=2)
        dot(a2, x, bb, c, t)
    for val, c, lab in [(low, t["s1"], "low-rate years"), (high, t["s2"], "high-rate years")]:
        a2.axhline(val, color=c, lw=1.2, alpha=.9, zorder=1)
    top_v, bot_v = (low, high) if low >= high else (high, low)
    for v_, lab_ in [(low, f"all low-rate years  {minus(low)}"), (high, f"all high-rate years  {minus(high)}")]:
        a2.text(years[-1] + 1.0, v_ + (0.06 if v_ == top_v else -0.06), lab_, color=t["ink"], fontsize=9,
                va="bottom" if v_ == top_v else "top")
    a2.plot([years[-1] + .45, years[-1] + .8], [low, low], color=t["s1"], lw=2, clip_on=False)
    a2.plot([years[-1] + .45, years[-1] + .8], [high, high], color=t["s2"], lw=2, clip_on=False)
    lim = max(1.6, float(np.nanpercentile(np.abs(b) + 1.96 * se, 90)))
    a2.set_ylim(-lim, lim)
    a2.set_ylabel("Payout ratio per unit of D/(D+E)")
    a2.set_xlim(years[0] - .8, years[-1] + .8)
    h1 = a2.scatter([], [], s=46, color=t["s1"]); h2 = a2.scatter([], [], s=46, color=t["s2"])
    a2.legend([h1, h2], ["low-rate year", "high-rate year"], loc="upper center", bbox_to_anchor=(0.5, -0.09),
              fontsize=9.5, ncol=2, labelcolor=t["ink2"])
    save(fig, path)


def h2_bounds(t, panel, outputs, path):
    """Regime effect per 1 SD of leverage, 95% CI, in every specification and leverage measure."""
    pw = pd.read_csv(outputs / "tab_power_bounds.csv")
    rows = [(r.specification, r.coef_payout, r.ci95_lo_payout, r.ci95_hi_payout) for r in pw.itertuples()]
    alt = pd.read_csv(outputs / "tab_alt_leverage.csv")
    alt = alt[(alt["dependent"] == "payout") & (alt["regime"] == "high-rate")].iloc[1:]   # row 0 = main measure
    extra = [(f"Leverage = {r._2}", r.interaction * r.sd_measure, (r.interaction - 1.96 * r.int_se) * r.sd_measure,
              (r.interaction + 1.96 * r.int_se) * r.sd_measure) for r in alt.itertuples()]
    items = rows + [None] + extra
    n = len(items)
    h = 0.34 * n + 2.1
    fig, ax = plt.subplots(figsize=(10, h))
    fig.subplots_adjust(left=0.34, right=0.97, top=1 - 1.25 / h, bottom=0.75 / h)
    titles(fig, t, "The rate regime doesn't move the payout–leverage slope",
           "Change in the payout ratio per 1 SD of leverage, high- minus low-rate years: estimate and 95% CI.\n"
           f"Shaded: ±{EQUIV_MARGIN:.2f}, about {EQUIV_MARGIN / panel['payout'].mean():.0%} of the mean payout, "
           "treated as economically negligible.",
           y=1 - 0.12 / h)
    ax.axvspan(-EQUIV_MARGIN, EQUIV_MARGIN, color=t["band"], lw=0, zorder=0)
    ax.axvline(0, color=t["base"], lw=1, zorder=1)
    labels = []
    for i, it in enumerate(items):
        y = n - 1 - i
        if it is None:
            labels.append(""); continue
        name, est, lo, hi = it
        main = i == 0
        c = t["s1"] if main else t["dim"]
        ax.plot([lo, hi], [y, y], color=c, lw=2 if main else 1.6, zorder=2)
        dot(ax, est, y, c, t, size=52 if main else 40)
        labels.append(re.sub(r"(\d{2})(\d{2})-(\d{2})\b", "\\1\\2–\\1\\3",
                             name.replace("Main (two-way FE)", "Main specification")
                             .replace("Driscoll-Kraay", "Driscoll–Kraay")))
    ax.set_yticks(range(n)); ax.set_yticklabels(labels[::-1])
    for lab in ax.get_yticklabels():
        if lab.get_text().startswith("Main"):
            lab.set_fontweight("bold"); lab.set_color(t["ink"])
    ax.grid(axis="y", visible=False)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlabel("Payout ratio per 1 SD of leverage")
    gap = n - 1 - len(rows)
    ax.text(ax.get_xlim()[0], gap, "  other leverage measures, per 1 SD of each:", color=t["ink2"], fontsize=9,
            va="center", style="italic")
    save(fig, path)


def h3(t, panel, outputs, path):
    """(a) High-rate change in the leverage slope across tangibility; (b) leave-one-out; (c) adjusted p-values."""
    r = fit_panel(panel, "payout", H3_REGS + CONTROLS, verbose=False)
    grid = np.linspace(0, 1, 41)
    est = np.array([lincom(r, {"lev_x_high": 1, "lev_x_high_x_tang": g})[:2] for g in grid])
    loo = pd.read_csv(outputs / "tab_H3_leave_one_out.csv")
    mt = pd.read_csv(outputs / "tab_multiple_testing.csv")

    fig = plt.figure(figsize=(12, 4.9))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.1, 1], wspace=0.42, left=0.06, right=0.985, top=0.74,
                          bottom=0.14)
    titles(fig, t, "Asset-light and asset-heavy industries respond in opposite directions – but not robustly",
           "H3 predicted that tangible industries are the stable ones. The estimate points the other way, leans on the "
           "2023–25 cycle and does not\nsurvive the multiple-testing adjustment: an exploratory pattern, not a finding.")
    a = fig.add_subplot(gs[0])
    a.fill_between(grid, est[:, 0] - 1.96 * est[:, 1], est[:, 0] + 1.96 * est[:, 1], color=t["s1"], alpha=.12, lw=0)
    a.plot(grid, est[:, 0], color=t["s1"])
    a.axhline(0, color=t["base"], lw=1)
    a.set_xlabel("Tangibility (PP&E / assets, percentile within year)")
    a.set_ylabel("High- minus low-rate leverage slope")
    a.set_title("Regime effect by tangibility", loc="left", fontsize=10.5, color=t["ink"])
    a.set_xlim(0, 1)

    b = fig.add_subplot(gs[1])
    groups = [("industry", "without one industry"), ("year", "without one year"),
              ("high-rate episode", "without one episode")]
    rng = np.random.default_rng(0)
    main = float(loo.loc[loo["dropped_type"] == "none (main)", "coef"].iloc[0])
    b.axvline(0, color=t["base"], lw=1)
    b.axvline(main, color=t["s1"], lw=1.4)
    for k, (typ, lab) in enumerate(groups):
        s = loo[loo["dropped_type"] == typ]
        y = len(groups) - 1 - k
        jit = rng.uniform(-0.18, 0.18, len(s)) if len(s) > 5 else np.zeros(len(s))
        worst = s["p"].idxmax()
        for (idx, row), j in zip(s.iterrows(), jit):
            hl = typ == "high-rate episode" and idx == worst
            dot(b, row["coef"], y + j, t["s2"] if hl else t["dim"], t, size=34 if len(s) > 5 else 46)
            if hl:
                b.text(row["coef"], y + 0.2, "without " + row["dropped"].replace("-20", "–"), ha="center",
                       va="bottom", fontsize=8.5, color=t["ink"])
        if typ == "high-rate episode":
            rest = s.drop(index=worst)
            b.text(rest["coef"].mean(), y - 0.22, "without " + " or ".join(
                d_.replace("-20", "–") for d_ in rest["dropped"]), ha="center", va="top", fontsize=8.5,
                color=t["ink2"])
    b.set_yticks(range(len(groups))); b.set_yticklabels([g[1] for g in groups][::-1])
    b.grid(axis="y", visible=False)
    b.set_ylim(-0.6, len(groups) - 0.35)
    b.set_xlabel("Triple interaction")
    b.set_title("Re-estimated without…", loc="left", fontsize=10.5, color=t["ink"])
    b.text(main, len(groups) - 0.42, f" all data {minus(main)}", color=t["ink2"], fontsize=8.5, va="bottom")

    c = fig.add_subplot(gs[2])
    m = mt.set_index(["family", "test"])
    prim = m.xs("Primary hypotheses").loc["H3: triple, PP&E rank"]
    fam = m.xs("H3 across tangibility measures").loc["H3: PP&E rank"]
    steps = [("Regression", prim["p"]), ("Cluster bootstrap", prim["p_bootstrap"]), ("Holm, H2 + H3", prim["p_holm"]),
             ("Romano–Wolf, H2 + H3", prim["p_romano_wolf"]), ("Romano–Wolf,\n5 tangibility measures", fam["p_romano_wolf"])]
    ys = np.arange(len(steps))[::-1]
    c.axvline(0.05, color=t["base"], lw=1)
    c.text(0.05, len(steps) - 0.45, " 0.05", color=t["muted"], fontsize=9, va="bottom")
    c.plot([p for _, p in steps], ys, color=t["dim"], lw=1.2, zorder=1)
    for (lab, p), y in zip(steps, ys):
        dot(c, p, y, t["s1"] if p < 0.05 else t["dim"], t, size=46)
        c.text(p + 0.008, y + 0.16, f"{p + 1e-9:.3f}", fontsize=9, color=t["ink"], va="bottom")
    c.set_yticks(ys); c.set_yticklabels([s[0] for s in steps])
    c.grid(axis="y", visible=False)
    c.set_xlim(0, max(0.22, max(p for _, p in steps) * 1.25)); c.set_ylim(-0.6, len(steps) - 0.3)
    c.set_xlabel("p-value of the triple term")
    c.set_title("Adjusted for multiple testing", loc="left", fontsize=10.5, color=t["ink"])
    save(fig, path)


def alignment(t, outputs, data_dirs, path):
    """The row-alignment check: leverage from wacc vs dbtfund in the flagged year, shifted rows highlighted."""
    al = pd.read_csv(outputs / "tab_data_check_alignment.csv")
    hit = al[(al["rows_set_missing"] > 0) & (al["file"] == "wacc")]
    if hit.empty:
        return False
    year = int(hit.iloc[0]["year"])
    sources = {tk: discover_sources(tk, data_dirs) for tk in TOKENS}
    if year not in sources.get("dbtfund", {}):
        return False
    r = load_year(year, sources)
    r = r[r["industry"].str.lower() != "total market"].dropna(subset=["lev", "lev_dbt"])
    by_count = r["nf_wacc"] != r["n_firms"]
    by_value = ~by_count & ((r["lev"] - r["lev_dbt"]).abs() / r[["lev", "lev_dbt"]].max(axis=1) >= 1e-3)
    bad = by_count | by_value
    n_count, n_value = int(by_count.sum()), int(by_value.sum())

    fig, ax = plt.subplots(figsize=(8.4, 7.0))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.76, bottom=0.1)
    titles(fig, t, f"A shifted block of rows in Damodaran's {year} wacc file",
           f"Each dot is an industry: its {year} leverage in wacc against the identical ratio in dbtfund. Aligned "
           f"rows sit on\nthe diagonal. {n_count} misaligned rows are caught by their firm counts; {n_value} more "
           f"has the same firm count as\nits neighbour and is caught by its value (ringed). All are set to missing.")
    top = float(max(r["lev"].max(), r["lev_dbt"].max())) * 1.08
    ax.plot([0, top], [0, top], color=t["base"], lw=1, zorder=1)
    dot(ax, r.loc[~bad, "lev_dbt"], r.loc[~bad, "lev"], t["dim"], t, size=34)
    dot(ax, r.loc[bad, "lev_dbt"], r.loc[bad, "lev"], t["s2"], t, size=46, zorder=5)
    if n_value:
        ax.scatter(r.loc[by_value, "lev_dbt"], r.loc[by_value, "lev"], s=190, facecolors="none",
                   edgecolors=t["ink"], linewidths=1.2, zorder=6)
        v = r[by_value].iloc[0]
        ax.annotate(f"{v['industry']}: same firm count\nas its neighbour, caught by value", (v["lev_dbt"], v["lev"]),
                    xytext=(0.005 * top / 0.7, 0.60 * top), textcoords="data", fontsize=9, color=t["ink"],
                    ha="left", va="bottom",
                    arrowprops=dict(arrowstyle="-", color=t["muted"], lw=0.8))
    ex = r[by_count].assign(gap=(r["lev"] - r["lev_dbt"]).abs()).sort_values("gap").iloc[-1]
    ax.annotate(f"{ex['industry']}\nwacc {ex['lev']:.2f} · dbtfund {ex['lev_dbt']:.2f}",
                (ex["lev_dbt"], ex["lev"]), xytext=(18, -30), textcoords="offset points", fontsize=9,
                color=t["ink"], arrowprops=dict(arrowstyle="-", color=t["muted"], lw=0.8))
    ax.set_xlim(0, top); ax.set_ylim(0, top); ax.set_aspect("equal")
    ax.set_xlabel("Market D/(D+E), dbtfund"); ax.set_ylabel("Market D/(D+E), wacc (as filed)")
    h1 = ax.scatter([], [], s=40, color=t["dim"]); h2 = ax.scatter([], [], s=46, color=t["s2"])
    ax.legend([h1, h2], ["lines up", "misaligned: set to missing"], loc="lower right", fontsize=9,
              labelcolor=t["ink2"])
    save(fig, path)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--outputs", type=Path, default=REPO / "outputs")
    p.add_argument("--data", type=Path, nargs="+", default=[REPO / "data"])
    p.add_argument("--img", type=Path, default=REPO / "docs" / "img")
    a = p.parse_args()
    panel_csv = a.outputs / "analysis_panel.csv"
    if not panel_csv.exists():
        sys.exit(f"{panel_csv} not found: run the notebook first (python scripts/run_notebook.py)")
    panel = pd.read_csv(panel_csv)
    a.img.mkdir(parents=True, exist_ok=True)
    made = []
    for mode in ["light", "dark"]:
        t = use(THEMES[mode])
        sfx = "" if mode == "light" else "-dark"
        hero(t, panel, a.img / f"hero{sfx}.png")
        h2_bounds(t, panel, a.outputs, a.img / f"h2_bounds{sfx}.png")
        h3(t, panel, a.outputs, a.img / f"h3_tangibility{sfx}.png")
        ok = alignment(t, a.outputs, a.data, a.img / f"data_alignment{sfx}.png")
        made += [f"hero{sfx}", f"h2_bounds{sfx}", f"h3_tangibility{sfx}"] + ([f"data_alignment{sfx}"] if ok else [])
    print("wrote", ", ".join(f"{m}.png" for m in made), "to", a.img)


if __name__ == "__main__":
    main()
