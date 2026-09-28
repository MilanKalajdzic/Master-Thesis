"""Two-way fixed-effects panel regressions.

`fit_panel` is the workhorse (linearmodels PanelOLS, industry and year effects, clustered or Driscoll-Kraay
standard errors). `fe_ols` computes the same estimates with plain numpy, about fifty times faster, for the
hundreds of refits in the leave-one-out and bootstrap checks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

try:
    from linearmodels.panel import PanelOLS
    HAVE_LM = True
except Exception:   # pragma: no cover
    HAVE_LM = False


def fit_panel(df, depvar, regressors, entity=True, time=True, cluster_time=False, title="",
              cov="clustered", weights=None, dk_bandwidth=3, verbose=True):
    """Panel OLS with industry/year effects. cov="clustered" (by industry, optionally also by year) or
    cov="kernel" (Driscoll-Kraay, robust to cross-sectional dependence); weights = column name or None."""
    say = print if verbose else (lambda *a, **k: None)
    d = df.dropna(subset=[depvar] + regressors + ([weights] if weights else [])).copy()
    ny = d["year"].nunique()
    say(f"=== {title} ===\nobs={len(d)}  industries={d['industry'].nunique()}  years={ny}")
    if ny < 3 or not HAVE_LM:
        if not HAVE_LM:
            say("linearmodels unavailable."); return None
        import statsmodels.formula.api as smf
        say("Short panel -> pooled OLS.\n")
        res = smf.ols(f"{depvar} ~ " + " + ".join(regressors), data=d).fit(cov_type="HC1")
        say(res.summary().tables[1]); return res
    import statsmodels.api as sm
    dd = d.set_index(["industry", "year"]); X = sm.add_constant(dd[regressors])
    mod = PanelOLS(dd[depvar], X, entity_effects=entity, time_effects=time, drop_absorbed=True,
                   weights=dd[weights] if weights else None)
    if cov == "kernel":
        res = mod.fit(cov_type="kernel", kernel="bartlett", bandwidth=dk_bandwidth)
    else:
        res = mod.fit(cov_type="clustered", cluster_entity=True, cluster_time=cluster_time)
    say(res.summary.tables[1]); say(f"R2(within): {res.rsquared_within:.3f}")
    absorbed = [r for r in regressors if r not in res.params.index]
    if absorbed:
        say("Absorbed by the fixed effects (not estimable, dropped):", absorbed)
    return res


def lincom(res, weights):
    """Linear combination sum_k w_k * b_k of a fitted model's coefficients: (estimate, SE, t)."""
    p = res.params
    cov = pd.DataFrame(np.asarray(res.cov if hasattr(res, "cov") else res.cov_params()),
                       index=p.index, columns=p.index)
    w = pd.Series(0.0, index=p.index)
    for k, v in weights.items():
        if k in w: w[k] = v
    est = float(w @ p); se = float(np.sqrt(w.values @ cov.values @ w.values))
    return est, se, (est / se if se else np.nan)


def fe_ols(y, X, ent, yr):
    """Two-way FE OLS with industry-clustered SE, in numpy.

    Industry effects are removed by demeaning and year effects enter as (demeaned) dummies, so the coefficients
    equal PanelOLS's exactly, and the SE use the same small-sample correction, n / (n - regressors - effects).
    `ent` and `yr` are integer codes starting at 0. Returns (coefficients, SE, residual degrees of freedom).
    """
    n, k = X.shape
    D = np.zeros((n, yr.max() + 1)); D[np.arange(n), yr] = 1.0
    Z = np.column_stack([y, X, D[:, 1:]])
    G = ent.max() + 1
    cnt = np.bincount(ent, minlength=G).astype(float)
    M = np.zeros((G, Z.shape[1])); np.add.at(M, ent, Z)
    Zd = Z - (M / np.maximum(cnt, 1)[:, None])[ent]
    yd, Xd = Zd[:, 0], Zd[:, 1:]
    Xd = Xd[:, np.r_[np.ones(k, bool), np.abs(Xd[:, k:]).sum(0) > 1e-10]]   # years absent from the sample
    A = np.linalg.pinv(Xd.T @ Xd)
    b = A @ (Xd.T @ yd); u = yd - Xd @ b
    S = np.zeros((G, Xd.shape[1])); np.add.at(S, ent, Xd * u[:, None])
    dof = n - Xd.shape[1] - int((cnt > 0).sum())
    V = A @ (S.T @ S) @ A * n / dof
    return b[:k], np.sqrt(np.diag(V)[:k]), dof


def spec_arrays(df, depvar, regs, term):
    """A specification as arrays for fe_ols: complete cases of depvar and regs; `term` is the tested one."""
    d = df.dropna(subset=[depvar] + regs)
    return {"y": d[depvar].to_numpy(float), "X": d[regs].to_numpy(float), "ind": d["industry"].to_numpy(),
            "year": d["year"].to_numpy(), "j": regs.index(term)}


def fit_arrays(s, mask=None):
    """Fit a spec_arrays specification (optionally on a subset of rows): (coef, SE, p, N) of the tested term."""
    y, X, ind, yrs = (s["y"], s["X"], s["ind"], s["year"]) if mask is None else \
                     (s["y"][mask], s["X"][mask], s["ind"][mask], s["year"][mask])
    b, se, dof = fe_ols(y, X, pd.factorize(ind)[0], np.unique(yrs, return_inverse=True)[1])
    j = s["j"]
    return b[j], se[j], 2 * stats.t.sf(abs(b[j] / se[j]), dof), len(y)
