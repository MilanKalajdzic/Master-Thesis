"""Multiple testing: Holm's step-down adjustment and the Romano-Wolf step-down bootstrap; placebo regime timing.

The bootstrap resamples whole industries (clusters) with replacement and refits every specification on the same
draw, so the joint distribution of the t-statistics, and hence the correlation between the tests, is kept. It does
not resample time: the placebo-timing check asks instead how unusual the actual high-rate years are among every
other placement of episodes of the same lengths.
"""
from __future__ import annotations

import numpy as np

from .estimation import fe_ols


def holm(p):
    """Holm (1979) step-down adjusted p-values."""
    p = np.asarray(p, float); out = np.empty_like(p); prev = 0.0
    for rank, i in enumerate(np.argsort(p)):
        prev = max(prev, min(1.0, (len(p) - rank) * p[i])); out[i] = prev
    return out


def cluster_bootstrap_t(specs, estimates, n_boot, seed, clusters):
    """Industry-cluster pairs bootstrap of t* = (b* - b) / se* for several specifications at once.

    specs: {name: spec_arrays(...)}; estimates: {name: original coefficient}; clusters: the industries to resample.
    A specification that appears under several names (the same object) is bootstrapped once.
    Returns {name: array of n_boot t-statistics}.
    """
    clusters = np.asarray(clusters)
    uniq = {}
    for name, s in specs.items():
        uniq.setdefault(id(s), name)
    rows = {name: {c: np.flatnonzero(specs[name]["ind"] == c) for c in clusters} for name in uniq.values()}
    rng = np.random.default_rng(seed)
    tstar = {name: np.empty(n_boot) for name in uniq.values()}
    for bb in range(n_boot):
        draw = rng.choice(clusters, size=len(clusters), replace=True)
        for name in uniq.values():
            s = specs[name]
            parts = [rows[name][c] for c in draw]
            idx = np.concatenate(parts)
            ent = np.repeat(np.arange(len(draw)), [len(p_) for p_ in parts])
            b_, se_, _ = fe_ols(s["y"][idx], s["X"][idx], ent, np.unique(s["year"][idx], return_inverse=True)[1])
            tstar[name][bb] = (b_[s["j"]] - estimates[name]) / se_[s["j"]]
    return {name: tstar[uniq[id(s)]] for name, s in specs.items()}


def bootstrap_p(t_obs, t_boot):
    """Two-sided bootstrap p-value of one test."""
    t_boot = np.asarray(t_boot)
    return (1 + (np.abs(t_boot) >= abs(t_obs)).sum()) / (1 + len(t_boot))


def romano_wolf(t_obs, t_boot):
    """Romano & Wolf (2005, 2016) step-down adjusted p-values.

    t_obs: observed t-statistics (one per test); t_boot: n_boot x tests matrix of centred bootstrap t-statistics.
    """
    t_obs = np.abs(np.asarray(t_obs, float)); T = np.abs(np.asarray(t_boot, float))
    out = np.empty(len(t_obs)); prev = 0.0
    order = np.argsort(-t_obs)
    for step, s in enumerate(order):
        max_t = T[:, order[step:]].max(axis=1)
        prev = max(prev, (1 + (max_t >= t_obs[s]).sum()) / (1 + len(max_t))); out[s] = prev
    return out


def episode_placements(years, lengths, min_gap=1):
    """Every placement of episodes with the given lengths (in this order) on the consecutive `years`, with at
    least `min_gap` years outside any episode between two of them. Returns a list of frozensets of years."""
    years = sorted(years)
    out = []

    def place(k, start, chosen):
        if k == len(lengths):
            out.append(frozenset(chosen))
            return
        rest = sum(lengths[k + 1:]) + min_gap * (len(lengths) - k - 1)      # room the later episodes need
        for s in range(start, len(years) - lengths[k] - rest + 1):
            place(k + 1, s + lengths[k] + min_gap, chosen + years[s:s + lengths[k]])

    place(0, 0, [])
    return out


def placebo_timing(fit, years, episodes, min_gap=1):
    """Placebo check of a regime interaction: refit with the high-rate episodes moved to every other placement.

    `fit(high_years)` returns the t-statistic of the tested term when `high_years` are the high-rate years;
    `episodes` are the actual episodes (lists of consecutive years), and the placebo episodes keep their lengths
    and order (episode_placements). Returns (t_obs, the t-statistic of every placement, p), p being the share of
    placements, the actual one included, whose |t| is at least |t_obs|. The placements are not equally likely under
    any model of monetary policy, so p says how special the actual timing is, not a probability under a null.
    """
    actual = frozenset(y for e in episodes for y in e)
    places = episode_placements(years, [len(e) for e in episodes], min_gap)
    if actual not in places:
        places.append(actual)
    t = np.array([fit(sorted(p)) for p in places])
    t_obs = t[places.index(actual)]
    return t_obs, t, float(np.mean(np.abs(t) >= abs(t_obs) - 1e-12))
