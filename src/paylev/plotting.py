"""Figure style shared by the thesis figures (the notebook) and the README figures (scripts/readme_figures.py).

Colours are tokens: two categorical series (blue, orange; validated for colour-vision deficiency and contrast on
every surface used here), a de-emphasis grey, ink for text, hairline grids. Marks carry colour; text never does.
Three themes: "print" (white page, sized for an A4 text width), "light" and "dark" (the README's two versions).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  base="#c3c2b7", s1="#2a78d6", s2="#eb6834", dim="#b4b2aa", wash="#2a78d6", band="#efeee9",
                  whisker=.55, neg="#e34948", mid="#f0efec"),
    "dark": dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 base="#383835", s1="#3987e5", s2="#d95926", dim="#5f5e59", wash="#3987e5", band="#262624",
                 whisker=.8, neg="#e66767", mid="#383835"),
}
THEMES["print"] = {**THEMES["light"], "surface": "#ffffff", "band": "#f1f0ec"}


def use(t, base_size=10.5):
    """Apply a theme to matplotlib (rcParams); returns the theme."""
    plt.rcParams.update({
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"], "savefig.facecolor": t["surface"],
        "font.family": "sans-serif", "font.size": base_size, "text.color": t["ink"],
        "axes.edgecolor": t["base"], "axes.labelcolor": t["ink2"], "axes.linewidth": 0.8,
        "axes.titlesize": base_size, "axes.titlecolor": t["ink"], "axes.titlelocation": "left",
        "axes.titlepad": 8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": t["grid"], "grid.linewidth": 0.8, "grid.linestyle": "-", "grid.alpha": 1,
        "xtick.color": t["muted"], "ytick.color": t["muted"], "xtick.labelcolor": t["ink2"],
        "ytick.labelcolor": t["ink2"], "xtick.major.size": 0, "ytick.major.size": 0,
        "legend.frameon": False, "legend.fontsize": base_size * 0.9, "lines.linewidth": 2,
        "lines.solid_capstyle": "round", "figure.figsize": (6.5, 3.6),
    })
    return t


def minus(v, fmt="+.2f"):
    """Signed number with a typographic minus; a value that rounds to zero prints unsigned (0.00, not −0.00)."""
    s = format(v, fmt)
    if not s.strip("+-0.%"):
        s = format(0.0, fmt.lstrip("+"))
    return s.replace("-", "−")


def titles(fig, t, title, subtitle, y=0.985):
    """Bold title and a grey subtitle at the top left of the figure (README figures)."""
    fig.text(0.012, y, title, fontsize=14, fontweight="bold", color=t["ink"], va="top")
    fig.text(0.012, y - 0.052, subtitle, fontsize=10, color=t["ink2"], va="top")


def dot(ax, x, y, color, t, size=46, zorder=4, **kw):
    """Filled marker with a ring in the surface colour, so it stays legible where it overlaps a line."""
    return ax.scatter(x, y, s=size, color=color, edgecolors=t["surface"], linewidths=1.6, zorder=zorder, **kw)


def runs(years, flags):
    """Consecutive years where flags is true, e.g. the high-rate episodes: [[1999, 2000, 2001], ...]."""
    out, cur = [], []
    for y, f in zip(years, flags):
        if f:
            cur.append(y)
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def shade(ax, episodes, t, alpha=.10, color=None):
    """Wash behind each episode (a list of year lists); the series-blue wash unless a colour is given."""
    for ep in episodes:
        ax.axvspan(ep[0] - .5, ep[-1] + .5, color=color or t["wash"], alpha=alpha, lw=0, zorder=0)


def diverging(t):
    """Diverging colormap for [-1, 1]: red (negative), neutral grey midpoint, blue (positive)."""
    return LinearSegmentedColormap.from_list("paylev_div", [t["neg"], t["mid"], t["s1"]])


def ink_on(rgba, t):
    """Ink or white text on a coloured cell, whichever contrasts more."""
    r, g, b = rgba[:3]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#ffffff" if lum < 0.5 else t["ink"]


def save(fig, path, dpi=200, close=True, quantize=True):
    """Save as a 256-colour PNG, about a third of the size of a full-colour one. The charts use a handful of flat
    colours plus anti-aliased edges; after octree quantisation each palette entry is set to the most frequent original
    colour it stands for, so the surface and series colours stay exact. quantize=False for figures with a continuous
    colour scale (heatmaps), where 256 colours would show as bands."""
    import numpy as np
    from PIL import Image
    fig.savefig(path, dpi=dpi)
    if close:
        plt.close(fig)
    if not quantize:
        return
    im = Image.open(path).convert("RGB")
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    rgb = np.asarray(im, dtype=np.int64).reshape(-1, 3)
    code = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
    keys, counts = np.unique((np.asarray(q, dtype=np.int64).ravel() << 24) | code, return_counts=True)
    idx, col = keys >> 24, keys & 0xFFFFFF
    order = np.lexsort((counts, idx))                   # by palette index, most frequent colour last
    last = np.r_[idx[order][1:] != idx[order][:-1], True]
    pal = q.getpalette()[:768]
    for k, c in zip(idx[order][last], col[order][last]):
        pal[3 * k:3 * k + 3] = [(c >> 16) & 255, (c >> 8) & 255, c & 255]
    q.putpalette(pal)
    q.save(path, optimize=True)


__all__ = ["THEMES", "use", "minus", "titles", "dot", "runs", "shade", "diverging", "ink_on", "save"]
