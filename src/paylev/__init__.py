"""paylev: the reusable parts of the thesis pipeline (payout, leverage and the interest-rate regime).

The notebook `thesis_analysis.ipynb` tells the story and makes the research choices (sample filters, industry
reconciliation, specifications); this package holds the machinery it calls, so that it can be tested:

    damodaran   find and read Damodaran's industry files across their three layouts, build one year's rows
    sample      reconcile industries, exclude financials, check that files line up, winsorise
    macro       FRED series: pinned snapshot or live download, annual averages, the rate regime
    estimation  two-way fixed-effects panel regressions (linearmodels, plus a fast numpy version for refits)
    inference   multiple-testing adjustments (Holm, Romano-Wolf) and the industry-cluster bootstrap
    synthetic   fake Damodaran files with known effects, for the tests
"""
__version__ = "1.0.0"
