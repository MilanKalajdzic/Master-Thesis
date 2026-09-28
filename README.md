# Does the Payout–Leverage Relationship Vary with the Interest Rate Regime?

**Industry-Level Evidence from US Non-Financial Firms, 1999–2025**

Master's thesis in Quantitative Finance, Faculty of Economic Sciences, University of Warsaw.
Author: Milan Kalajdžić · Supervisor: dr hab. Piotr Boguszewski · *Work in progress*

This repository contains the full empirical pipeline: data loading, sample construction, estimation,
robustness checks, tables and figures. It uses only public data (Damodaran, NYU Stern and FRED), so
every number can be reproduced from scratch.

---

## Research question and hypotheses

Does the relationship between corporate leverage and payout policy depend on whether interest rates are
high or low?

| | Hypothesis | Test | Expected |
|---|---|---|---|
| **H1** | More leveraged industries pay out less when rates rise (debt service crowds out distributions) | leverage × high-rate | < 0 |
| **H2** | The payout–leverage sensitivity is stronger in high-rate regimes *(main contribution)* | β₂ on leverage × high-rate | β₂ < 0 |
| **H3** | High asset tangibility stabilises the relationship across regimes (lower refinancing risk) | leverage × high-rate × tangibility | > 0 |

## Data and method

- **Panel:** 143 non-financial, non-utility US industries × 27 years (1999–2025), 2,116 industry-years;
  a *stable core* of 46 industries present ≥ 20 years is used as a robustness sample.
- **Sources:** Damodaran industry files `divfund` (payout, ROE, market cap), `divfcfe` (dividends, FCFE),
  `wacc` (market leverage D/(D+E), tax rate), `dbtfund` (PP&E / total assets, book and lease-free leverage,
  EBITDA/EV), `capex` (capex-based tangibility proxies); FRED (fed funds rate, 10y Treasury, BAA–AAA spread,
  real GDP).
- **Tangibility (H3):** PP&E / total assets, as the industry's percentile rank within each year (the variable's
  definition changes in 2013 and 2017, see the data-quality notes).
- **Rate regime:** a year is *high-rate* if the annual-average fed funds rate is ≥ 3%, which gives three
  separate episodes (1999–2001, 2005–2007, 2023–2025). A post-2022 dummy and the continuous rate are
  reported as alternatives.
- **Model:** two-way fixed effects (industry and year), standard errors clustered by industry:

$$\text{payout}_{it}=\beta_1\,\text{lev}_{it}+\beta_2\,(\text{lev}_{it}\times\text{HighRate}_t)+\gamma_1\text{ROE}_{it}+\gamma_2\text{tax}_{it}+\gamma_3\text{size}_{it}+\alpha_i+\delta_t+\varepsilon_{it}$$

Year fixed effects absorb every variable that only varies over time (the regime dummy, GDP growth, the
credit spread). Those variables enter through interactions, or in a separate industry-FE-only specification.

## Results (current)

Payout ratios are only defined for positive earnings, so industry-years with ROE ≤ 0 are excluded from the
payout-ratio models (1,894 observations; see the data-quality notes).

**Leverage and payout.** Leverage is *positively* related to payout: +0.299 (SE 0.140, p = 0.033) with
industry and year fixed effects. More levered industries pay out more, the opposite of the substitution
(free-cash-flow) story behind H1 and in line with the complementarity view. The estimate survives
standard errors robust to common shocks and weighting by the number of firms, but not first differences,
where it is small and imprecise (its interval still contains +0.30). It is best read as a slow-moving,
medium-run association, consistent with smoothed dividends, rather than a year-to-year response
([stress test](outputs/tab_stress_leverage.csv)):

| Stress test | Leverage coef. | SE | p | β₂ (lev × high) | p | N |
|---|---:|---:|---:|---:|---:|---:|
| Industry-clustered SE (main) | +0.299 | 0.140 | 0.033 | −0.041 | 0.774 | 1894 |
| Two-way clustered SE | +0.299 | 0.151 | 0.048 | −0.041 | 0.768 | 1894 |
| Driscoll–Kraay SE (3 lags) | +0.299 | 0.111 | 0.007 | −0.041 | 0.775 | 1894 |
| First differences (+ year FE) | +0.109 | 0.335 | 0.744 | −0.060 | 0.652 | 1640 |
| Weighted by number of firms | +0.328 | 0.163 | 0.044 | −0.033 | 0.823 | 1894 |

**H2: not supported.** The regime interaction is close to zero and nowhere near significance
(β₂ = −0.041, SE 0.141, p = 0.77); the leverage slope is +0.314 in low-rate years and +0.274 in high-rate
years. The null holds in every specification:

| Specification | Term | Coef. | SE | p | N |
|---|---|---:|---:|---:|---:|
| Main (two-way FE) | lev × high | −0.041 | 0.141 | 0.774 | 1894 |
| Stable core (46 industries) | lev × high | −0.089 | 0.176 | 0.614 | 1089 |
| Regime = post-2022 dummy | lev × high | −0.166 | 0.265 | 0.531 | 1894 |
| Continuous rate | lev × FFR | −0.003 | 0.033 | 0.917 | 1894 |
| DV = Dividends / FCFE | lev × high | −0.262 | 0.657 | 0.690 | 1602 |
| DV = Dividend yield (D/MC) | lev × high | +0.007 | 0.004 | 0.118 | 2087 |
| Two-way clustered SE | lev × high | −0.041 | 0.137 | 0.768 | 1894 |
| Excluding 2020–21 | lev × high | −0.068 | 0.149 | 0.646 | 1771 |
| Lagged leverage | lev(t−1) × high | −0.043 | 0.160 | 0.789 | 1764 |
| Industry FE + macro controls | lev × high | −0.144 | 0.156 | 0.356 | 1894 |
| Backward elimination of controls | lev × high | −0.042 | 0.143 | 0.767 | 1894 |
| Payout as reported (incl. ROE ≤ 0) | lev × high | −0.018 | 0.138 | 0.894 | 2004 |
| Driscoll–Kraay SE | lev × high | −0.041 | 0.142 | 0.775 | 1894 |
| First differences | Δ(lev × high) | −0.060 | 0.133 | 0.652 | 1640 |
| Weighted by number of firms | lev × high | −0.033 | 0.147 | 0.823 | 1894 |

**How large an effect can we rule out?** A null result is only informative if the test could have found a
meaningful effect. In the main specification the 95% interval for β₂ is [−0.317, +0.236]. Scaled by the
standard deviation of leverage (0.139), this rules out regime effects larger than 0.044 in the payout ratio per
1 SD of leverage (12% of the mean payout of 0.37); an equivalence test (TOST) rejects effects above 0.038 at the
5% level. The test has 80% power only for effects of about 0.055 (15% of the mean), so smaller effects cannot be
excluded. Across the other specifications the bound is 0.040–0.063, except the post-2022 dummy (0.095), which
uses the least regime variation ([table](outputs/tab_power_bounds.csv)).

**Other leverage measures.** H1 is about debt *service*, and market D/(D+E) is only a rough gauge of it: it moves
with share prices and includes capitalised leases from 2013 on. Interest coverage is only reported from 2022, so
the closest panel measure is Debt/EBITDA (debt relative to operating cash flow), built as D/(D+E) ÷ (EBITDA/EV)
and checked against Damodaran's own figure where he reports it. The positive leverage–payout relation holds for
every measure, and the regime interaction is null for every measure, including Debt/EBITDA × the fed funds
rate, the nearest thing to an interest-burden test ([table](outputs/tab_alt_leverage.csv)):

| Leverage measure | Leverage coef. | p | × high-rate | p | per 1 SD | 95% bound per SD | N |
|---|---:|---:|---:|---:|---:|---:|---:|
| Market D/(D+E), main (leases from 2013) | +0.299 | 0.033 | −0.041 | 0.774 | −0.006 | 0.044 | 1894 |
| Market D/(D+E), without leases | +0.326 | 0.017 | −0.050 | 0.736 | −0.007 | 0.046 | 1894 |
| Book D/(D+E) | +0.619 | < 0.001 | −0.011 | 0.902 | −0.002 | 0.029 | 1892 |
| Debt / EBITDA | +0.049 | 0.003 | −0.011 | 0.542 | −0.016 | 0.067 | 1891 |
| Debt / EBITDA × fed funds rate (per pp) | | | +0.000 | 0.973 | +0.000 | 0.011 | 1891 |

Two caveats. Debt/EBITDA and the payout ratio both have earnings in the denominator; with the dividend yield as
the dependent variable the Debt/EBITDA coefficient is zero (p = 0.89), so its positive link with payout may be
partly mechanical. Book leverage rises mechanically when payouts shrink book equity, and it is missing where book
equity is negative (restaurants and tobacco in recent years).

**H3: not supported; the estimate points the other way.** With tangibility measured as PP&E / total assets, the
triple interaction is −1.09 (SE 0.49, p = 0.027). In high-rate years the leverage–payout slope *rises* by 0.47
(p = 0.04) for the least tangible industries (10th percentile) and *falls* by 0.41 (p = 0.12) for the most
tangible (90th percentile). H3 expected tangible industries to be the stable ones. The sign survives
Driscoll–Kraay and two-way clustered errors, dropping 2020–21, weighting by firms, the continuous rate, a
time-invariant tangibility (−1.01, p = 0.043) and two of the three capex-based proxies (Net Cap Ex/Sales
p = 0.027, Capital/Sales p = 0.039; Cap Ex/Depreciation −0.17, p = 0.30). It is not significant in the stable
core (−0.60, p = 0.33) ([sensitivity](outputs/tab_H3_robustness.csv), [proxies](outputs/tab_H3_proxy_robustness.csv)).

**Is the H3 result fragile?** ([leave-one-out](outputs/tab_H3_leave_one_out.csv),
[multiple testing](outputs/tab_multiple_testing.csv))
- *No single industry drives it.* Dropping any one of the 141 industries leaves the term between −1.25 and −0.87,
  significant at 5% in 138 cases and at 10% in all.
- *It leans on the latest tightening cycle.* Dropping 1999–2001 or 2005–2007 leaves it at −1.33 (p = 0.04) and
  −1.28 (p = 0.05); dropping 2023–2025 halves it to −0.60 (p = 0.14). Dropping 2023 alone gives −0.71
  (p = 0.11), while every other single year keeps p < 0.05.
- *It does not survive the multiple-testing adjustment.* The industry-cluster bootstrap gives p = 0.047
  unadjusted. Adjusted for testing H2 and H3 together, p = 0.055 (Holm) and 0.076 (Romano–Wolf); adjusted
  across the five tangibility measures, p = 0.18 (Romano–Wolf).

So H3 is not supported, and the opposite pattern (the payout–leverage link weakening in high-rate years for
asset-heavy industries and strengthening for asset-light ones) is exploratory: it comes mostly from the 2023–2025
cycle and is not established once the number of tests is accounted for. It is still a reason not to read the H2
null as "no effect anywhere": opposite responses may average out.

**Other findings.**
- The strong negative ROE coefficient is mechanical. ROE is negatively related to the payout ratio
  (−1.59, p < 0.001) and to Dividends/FCFE (−2.85, p < 0.001), but both contain net income in the denominator
  (FCFE includes net income). With dividend yield (dividends ÷ market cap), which contains no earnings, the
  ROE coefficient is +0.004 (p = 0.07): more profitable industries do not pay out less
  ([table](outputs/tab_roe_check.csv)). The leverage coefficient in the yield regression is not interpreted,
  because yield and D/(D+E) both contain market equity.
- The effective tax rate is negatively related to payout (−0.48, p = 0.004).
- Tangibility itself is not related to payout once industry effects are in (PP&E rank +0.15, p = 0.28). With
  the Cap Ex/Depreciation proxy it was negative (−0.075, p = 0.010), which mostly reflects investment intensity
  rather than asset tangibility.

**Dividend smoothing (Lintner, 1956).** Industry dividends adjust slowly toward a target payout: the speed of
adjustment is between 0.09 and 0.36 per year (pooled vs within estimates, which bracket the true value), with a
target payout of 0.28, close to the median payout ratio. The payout *ratio* itself is far less persistent
(0.13–0.43), because it moves with earnings. Smoothing does not differ between rate regimes, and H1 tested
in change form (do more levered industries cut dividends more when rates are high or rising?) is not supported.
These change models drop 2013, when Damodaran's reclassification moves firms between industries (industry
dividends jump by a median 42% that year vs 10–20% otherwise):

| Change-form test of H1 | Coef. | SE | p | N |
|---|---:|---:|---:|---:|
| lev(t−1) × high-rate year | +0.0016 | 0.0039 | 0.675 | 1771 |
| lev(t−1) × hiking year (fed funds up ≥ 25bp) | +0.0015 | 0.0023 | 0.505 | 1771 |
| lev(t−1) × change in fed funds rate | +0.0006 | 0.0009 | 0.518 | 1771 |
| lev(t−1) × high-rate year, stable core | +0.0022 | 0.0030 | 0.465 | 1026 |

Interpretation: over three full rate cycles, more levered industries pay out more, industry dividends are
smoothed, and on average neither the payout–leverage link nor the smoothing re-rates with the cost of debt beyond
the bounds above, whichever leverage measure is used. The one hint of regime dependence is the split by
tangibility (H3), where asset-heavy and asset-light industries appear to move in opposite directions, mostly in
the 2023–2025 cycle; it does not survive the multiple-testing adjustment.
All results are associational.

<p align="center"><img src="outputs/fig_coefficient_forest.png" width="620"></p>

## Data-quality notes

- **Capex depreciation break (2013–2015).** In Damodaran's 2013–2015 capex files, industry depreciation
  roughly halves while capex does not (Total Market: $908bn in 2012 → $368bn in 2013 → $719bn in 2016).
  This inflates Cap Ex/Depreciation and scrambles the industry ranking, so the depreciation-based proxies
  (robustness checks for H3) are set to missing in those years ([figure](outputs/fig_data_check_tangibility.png),
  [table](outputs/tab_data_check_yearly_medians.csv)).
- **Industry reclassification (2012→2013).** Damodaran moved to a new industry scheme. Names are
  reconciled with a conservative rename map ([Appendix B](outputs/appendix_B_rename_map.csv)), and the
  stable-core sample checks that nothing hinges on it.
- **Leverage and leases (2013).** From 2013 on, `wacc`'s D/(D+E) capitalises operating leases (it equals
  `dbtfund`'s lease-adjusted ratio exactly); before 2013 it equals the unadjusted ratio. The main leverage measure
  therefore changes definition in 2013, most for lease-heavy industries. Since 2019 (ASC 842) leases are on the
  balance sheet and the two ratios almost coincide. The lease-free ratio gives the same results (table above).
- **PP&E / assets (2013, 2016, 2017).** `dbtfund` reports Fixed Assets / BV of Capital (1999–2012), Fixed Assets /
  Total Assets (2013–2016) and Net PP&E / Total Assets (2017+). The median drifts down over time and the industry
  ordering reshuffles in 2013 and 2016 (rank correlation with the previous year 0.78 and 0.83, against 0.96–0.99
  otherwise, [table](outputs/tab_data_check_ppe_rank_stability.csv)). Tangibility is therefore used as a
  within-year percentile rank, and the time-invariant H3 variant averages over the reshuffles.
- **Debt / EBITDA.** Damodaran reports it only in 2018 and 2022+, so it is built from D/(D+E) and EBITDA/EV. In
  the years where both exist the two rank industries alike (rank correlation 0.87–0.96); the constructed level is
  about 10–20% lower because EV nets out cash ([table](outputs/tab_data_check_debt_ebitda.csv)). Interest
  coverage, the direct measure of debt-service burden, exists only from 2022 on and is not used.
- **Row alignment (1999).** An industry has the same number of firms in every file of a year, so matching
  firm counts across files confirm that each row belongs to its name. They match everywhere except in
  `wacc99`, where 17 industries (Aluminum to Chemical (Specialty)) are shifted by one row: Auto & Truck, for
  example, carries Apparel's leverage (0.18 instead of 0.51). Leverage and the tax rate are set to missing for
  those rows ([table](outputs/tab_data_check_alignment.csv)); this removes 11 observations from the
  payout-ratio models.
- **Cross-file check (2000, 2007).** `divfund`'s payout ratio should equal dividends ÷ net income from
  `divfcfe`; it does (within 5%) for 91–100% of industries in every year except 2000 and 2007. In
  `divfcfe07` the net-income column does not match the listed industries. Measures built from `divfcfe`
  are excluded in those years ([table](outputs/tab_data_check_crossfile.csv)); the main payout variable
  comes from `divfund` and is unaffected.
- **Undefined ratios.** Payout (dividends ÷ earnings), Dividends/FCFE and total payout ÷ net income are
  meaningless when the denominator is ≤ 0, yet the files report values there: 110 loss-making industry-years
  have a median payout of 0.003 although they pay dividends, and 318 have a negative Dividends/FCFE. These are
  set to missing (`POSITIVE_DENOMINATORS` in the configuration); the as-reported payout is kept as a
  robustness check.
- **Heterogeneous layouts.** File layouts differ across three eras (sheet names, header rows, column
  names). The loader finds the table, the columns and the data year automatically.

## Reproduce

```bash
git clone https://github.com/MilanKalajdzic/Master-Thesis.git
cd Master-Thesis
pip install -r requirements.txt           # or requirements-lock.txt for the exact tested versions
python scripts/download_damodaran.py      # 135 files -> data/raw/  (see data/README.md)
jupyter nbconvert --to notebook --execute --inplace thesis_analysis.ipynb
```

Or open `thesis_analysis.ipynb` and run all cells. Tables and figures are written to `outputs/`.
FRED data come from a pinned snapshot (`data/fred/fred_snapshot.csv`, vintage 2026-09-28), so results
match exactly. Set `FRED_SOURCE = "live"` in the configuration cell to download the current vintage.
A full run takes under a minute; the bootstrap in §10b is seeded (`RW_SEED`), so it reproduces too.

## Repository layout

```
thesis_analysis.ipynb        full pipeline (sections map to thesis chapters 4-6 and appendices)
scripts/
  download_damodaran.py      fetches the 135 Damodaran industry files (5 datasets, 1999-2025)
  refresh_fred_snapshot.py   re-downloads the FRED series into the snapshot
data/
  raw/                       Damodaran .xls files (not committed; downloaded)
  fred/fred_snapshot.csv     FRED monthly/quarterly series used in the thesis
outputs/                     regression tables (CSV + LaTeX), robustness tables, appendices, figures
```

## Limitations

Industry aggregation hides firm heterogeneity. The data are a repeated cross-section of industry
averages, not a firm panel. Tangibility (PP&E / assets) changes definition over time, so only its within-year
ranking is used. Payout ratios are noisy when earnings are
near zero (winsorised at 1%/99%). Identification is associational, not causal.

## License

Code: Apache-2.0 (see `LICENSE`). Data belong to their providers: Aswath Damodaran (NYU Stern) and the
Federal Reserve Bank of St. Louis (FRED).
