import numpy as np
import pytest

from paylev.estimation import fit_arrays, spec_arrays
from paylev.inference import bootstrap_p, cluster_bootstrap_t, holm, romano_wolf
from tests.test_estimation import make_panel


def test_holm_known_values():
    assert np.allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    assert np.allclose(holm([0.5, 0.6]), [1.0, 1.0])               # capped at 1
    assert np.allclose(holm([0.02]), [0.02])


def test_romano_wolf_with_one_test_is_the_bootstrap_p():
    rng = np.random.default_rng(0)
    tb = rng.standard_normal((999, 1))
    assert romano_wolf([2.0], tb)[0] == pytest.approx(bootstrap_p(2.0, tb[:, 0]))


def test_romano_wolf_adjusts_up_and_keeps_the_order():
    rng = np.random.default_rng(1)
    tb = rng.standard_normal((1999, 4))
    t = [3.0, -2.2, 1.0, 0.3]
    p_rw = romano_wolf(t, tb)
    p_single = [bootstrap_p(ti, tb[:, j]) for j, ti in enumerate(t)]
    assert np.all(p_rw >= np.array(p_single) - 1e-12)
    assert list(np.argsort(p_rw)) == list(np.argsort(-np.abs(t)))
    tc = np.column_stack([tb[:, 0]] * 4)                           # perfectly correlated tests: no penalty
    assert np.allclose(romano_wolf([2.0] * 4, tc), bootstrap_p(2.0, tb[:, 0]))


def test_cluster_bootstrap_is_reproducible_and_centred():
    df = make_panel(seed=5)
    s = spec_arrays(df, "y", ["x", "z"], "x")
    est = {"a": fit_arrays(s)[0], "b": fit_arrays(s)[0]}
    specs = {"a": s, "b": s}                                       # same spec twice: bootstrapped once
    t1 = cluster_bootstrap_t(specs, est, 200, seed=7, clusters=sorted(set(df["industry"])))
    t2 = cluster_bootstrap_t(specs, est, 200, seed=7, clusters=sorted(set(df["industry"])))
    assert np.array_equal(t1["a"], t2["a"]) and np.array_equal(t1["a"], t1["b"])
    assert abs(np.mean(t1["a"])) < 0.3 and 0.6 < np.std(t1["a"]) < 1.6
