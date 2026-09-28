import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from paylev.plotting import THEMES, minus, runs, save, use


def test_minus_uses_a_typographic_minus_and_an_unsigned_zero():
    assert minus(-0.041, "+.3f") == "−0.041"
    assert minus(0.298) == "+0.30"
    assert minus(-0.001) == "0.00"          # rounds to zero: no sign
    assert minus(-0.001, "+.1%") == "−0.1%"


def test_runs_groups_consecutive_years():
    years = [1999, 2000, 2001, 2002, 2003, 2004, 2005]
    flags = [True, True, False, False, True, False, True]
    assert runs(years, flags) == [[1999, 2000], [2003], [2005]]
    assert runs(years, [False] * 7) == []


def test_save_keeps_the_series_colours_exact(tmp_path):
    t = use(THEMES["print"])
    fig, ax = plt.subplots(figsize=(2, 1.5))
    ax.bar([0, 1], [1, 2], color=[t["s1"], t["s2"]])
    save(fig, tmp_path / "q.png", dpi=80)
    im = Image.open(tmp_path / "q.png")
    assert im.mode == "P"
    colours = {"#%02x%02x%02x" % c for _, c in im.convert("RGB").getcolors(256)}
    assert {t["s1"], t["s2"], t["surface"]} <= colours

    fig, ax = plt.subplots(figsize=(2, 1.5))
    ax.imshow([[0, 1], [2, 3]])
    save(fig, tmp_path / "full.png", dpi=80, quantize=False)
    assert Image.open(tmp_path / "full.png").mode == "RGBA"
