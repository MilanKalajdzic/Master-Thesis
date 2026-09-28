import numpy as np
import pandas as pd
import pytest

from paylev.estimation import fe_ols, fit_arrays, fit_panel, lincom, spec_arrays


def make_panel(seed=0, n_ind=40, years=range(2000, 2016), missing=0.15):
    """Unbalanced panel with industry and year effects and a known slope of 0.5 on x."""
    rng = np.random.default_rng(seed)
    rows = []
    a = rng.normal(0, 1, n_ind); d = {y: rng.normal(0, 1) for y in years}
    for i in range(n_ind):
        for y in years:
            if rng.random() < missing:
                continue
            x, z = rng.normal(a[i], 1), rng.normal(0, 1)
            rows.append({"industry": f"ind{i:02d}", "year": y, "x": x, "z": z, "w": rng.uniform(1, 5),
                         "y": 0.5 * x - 0.2 * z + a[i] + d[y] + rng.normal(0, 0.2 + 0.1 * (i % 3))})
    df = pd.DataFrame(rows)
    df["trait"] = df["industry"].str[-2:].astype(int) / 10.0          # time-invariant: absorbed
    return df


def test_fit_panel_recovers_the_slope():
    r = fit_panel(make_panel(), "y", ["x", "z"], verbose=False)
    assert r.params["x"] == pytest.approx(0.5, abs=0.08) and r.params["z"] == pytest.approx(-0.2, abs=0.08)


def test_fast_estimator_matches_panelols():
    df = make_panel(seed=1)
    r = fit_panel(df, "y", ["x", "z"], verbose=False)
    s = spec_arrays(df, "y", ["x", "z"], "x")
    b, se, p, n = fit_arrays(s)
    assert b == pytest.approx(r.params["x"], abs=1e-10)
    assert se == pytest.approx(r.std_errors["x"], abs=1e-10)       # same small-sample correction
    assert p == pytest.approx(r.pvalues["x"], abs=1e-10) and n == r.nobs


def test_fast_estimator_on_a_subset_matches_a_refit():
    df = make_panel(seed=2)
    s = spec_arrays(df, "y", ["x", "z"], "z")
    keep = s["ind"] != "ind03"
    b, se, _, n = fit_arrays(s, keep)
    r = fit_panel(df[df["industry"] != "ind03"], "y", ["x", "z"], verbose=False)
    assert b == pytest.approx(r.params["z"], abs=1e-10) and se == pytest.approx(r.std_errors["z"], abs=1e-10)


def test_fe_ols_ignores_empty_entities_and_missing_years():
    df = make_panel(seed=3)
    df = df[df["year"] != 2003]                                   # a year absent from the sample
    ent = pd.factorize(df["industry"])[0] + 1                      # entity code 0 has no rows
    yr = np.unique(df["year"], return_inverse=True)[1]
    b1, se1, _ = fe_ols(df["y"].to_numpy(), df[["x", "z"]].to_numpy(), ent, yr)
    b0, se0, _ = fe_ols(df["y"].to_numpy(), df[["x", "z"]].to_numpy(), ent - 1, yr)
    assert np.allclose(b1, b0) and np.allclose(se1, se0)


@pytest.mark.filterwarnings("ignore::linearmodels.panel.utility.AbsorbingEffectWarning")   # the point of the test
def test_absorbed_regressors_are_reported(capsys):
    r = fit_panel(make_panel(), "y", ["x", "trait"], title="absorbed")
    assert "trait" not in r.params.index
    assert "Absorbed by the fixed effects" in capsys.readouterr().out


# Two-way clustered variances (industry + year - intersection) can come out negative for the constant, whose
# SE linearmodels then reports as NaN with a RuntimeWarning; the slopes are unaffected (and checked here).
@pytest.mark.filterwarnings("ignore:invalid value encountered in sqrt:RuntimeWarning")
def test_other_covariances_and_weights_run():
    df = make_panel(seed=4)
    for kw in [dict(cov="kernel"), dict(cluster_time=True), dict(weights="w"), dict(time=False)]:
        r = fit_panel(df, "y", ["x", "z"], verbose=False, **kw)
        assert r.params["x"] == pytest.approx(0.5, abs=0.1), kw
        assert r.std_errors[["x", "z"]].notna().all(), kw


def test_lincom_is_a_sum_of_coefficients():
    r = fit_panel(make_panel(), "y", ["x", "z"], verbose=False)
    est, se, t = lincom(r, {"x": 1, "z": 1, "not_there": 5})
    assert est == pytest.approx(r.params["x"] + r.params["z"])
    V = r.cov.loc[["x", "z"], ["x", "z"]].to_numpy()
    assert se == pytest.approx(np.sqrt(V.sum())) and t == pytest.approx(est / se)
