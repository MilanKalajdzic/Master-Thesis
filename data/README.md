# Data

## Damodaran industry files (`data/raw/`, not committed)

Four US industry datasets from Aswath Damodaran's archive (NYU Stern), one file per data year, 1999–2025:

| Token | Contents used | Example |
|---|---|---|
| `divfund` | Dividend payout ratio, ROE, market cap | `divfund24.xls` |
| `divfcfe` | Dividends, FCFE, (dividends + buybacks), net income | `divfcfe24.xls` |
| `wacc` | Market debt ratio D/(D+E), effective tax rate | `wacc24.xls` |
| `capex` | Cap Ex / Depreciation, Net Cap Ex / Sales, Sales / Capital | `capex24.xls` |

Download everything with:

```bash
python scripts/download_damodaran.py
```

**Naming.** The two-digit suffix is the *data* year. Each archive file is the January update of the
following year, so `archives/wacc24.xls` (listed as "1/25" on the archive page) holds 2024 data. The newest
year is not archived yet: it is the current file (`pc/datasets/wacc.xls`) and gets saved as `wacc25.xls`.
The notebook reads the year from each file's internal "Date updated" stamp where there is one (2018+),
so a mislabelled newest file is still dated correctly.

Manual download: <https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html>. Firefox or
Edge work more reliably than Chrome on that site. Files can sit anywhere under `data/`; the loader
searches recursively.

## FRED snapshot (`data/fred/fred_snapshot.csv`, committed)

Long format (`series_id, date, value`), vintage 2026-09-28:

| Series | Frequency | Used as |
|---|---|---|
| `FEDFUNDS` | monthly | rate regime (annual average ≥ 3%), continuous rate |
| `GS10` | monthly | 10-year Treasury yield (descriptive) |
| `BAA`, `AAA` | monthly | credit spread = BAA − AAA |
| `GDPC1` | quarterly | real GDP growth |

Annual values are simple averages of the monthly/quarterly observations. Refresh with
`python scripts/refresh_fred_snapshot.py`. Real GDP is revised, so a new vintage can move the
macro-control estimates slightly.
