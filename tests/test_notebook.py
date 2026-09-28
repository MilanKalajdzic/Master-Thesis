"""The whole notebook, run on fake Damodaran files (see paylev/synthetic.py) with the committed FRED snapshot.

It must run without errors, produce every output the repo ships, find the planted effects and catch the
planted data defects.
"""
import json
import os
import subprocess
import sys

import pandas as pd
import pytest

from paylev.synthetic import SCRAMBLED, SHIFTED, TRUTH
from tests.conftest import REPO


@pytest.fixture(scope="module")
def run(fake_dir, tmp_path_factory):
    pytest.importorskip("nbclient"); pytest.importorskip("nbformat"); pytest.importorskip("ipykernel")
    out = tmp_path_factory.mktemp("run")
    env = {**os.environ, "PAYLEV_DATA": str(fake_dir), "PAYLEV_OUTDIR": str(out / "outputs"),
           "PAYLEV_RW_BOOT": "49", "MPLBACKEND": "Agg"}
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "run_notebook.py"), "--output", str(out / "nb.ipynb")],
                          capture_output=True, text=True, timeout=1200, env=env)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return out


def coef(cell):
    """'0.307*** (0.010)' -> 0.307"""
    return float(str(cell).split()[0].rstrip("*"))


def test_runs_without_errors(run):
    nb = json.loads((run / "nb.ipynb").read_text())
    errors = [o for c in nb["cells"] if c["cell_type"] == "code" for o in c.get("outputs", [])
              if o.get("output_type") == "error"]
    assert not errors
    assert nb["metadata"]["kernelspec"]["name"] == "python3"


def test_writes_every_output_the_repo_ships(run):
    shipped = subprocess.run(["git", "ls-files", "outputs"], cwd=REPO, capture_output=True, text=True).stdout.split()
    if not shipped:
        pytest.skip("not a git checkout")
    made = {p.name for p in (run / "outputs").iterdir()}
    assert {os.path.basename(f) for f in shipped} <= made


def test_finds_the_planted_effects(run):
    tab = pd.read_csv(run / "outputs" / "tab_regressions_combined.csv", index_col=0)
    assert coef(tab.loc["lev", "Interaction"]) == pytest.approx(TRUTH["lev"], abs=0.05)
    assert coef(tab.loc["lev_x_high", "Interaction"]) == pytest.approx(TRUTH["lev_x_high"], abs=0.05)
    assert coef(tab.loc["roe", "Interaction"]) == pytest.approx(TRUTH["roe"], abs=0.1)
    verdicts = (run / "outputs" / "hypothesis_verdicts.txt").read_text()
    assert "H1/H2" in verdicts and "-> SUPPORTED" in verdicts.splitlines()[0]


def test_catches_the_planted_data_defects(run):
    token, year, a, b = SHIFTED
    al = pd.read_csv(run / "outputs" / "tab_data_check_alignment.csv")
    assert al.loc[(al["file"] == token) & (al["year"] == year), "rows_set_missing"].item() == b - a
    assert al.loc[~((al["file"] == token) & (al["year"] == year)), "rows_set_missing"].eq(0).all()
    cf = pd.read_csv(run / "outputs" / "tab_data_check_crossfile.csv", index_col=0)["share_agree"]
    assert cf.loc[SCRAMBLED[1]] < 0.75 and cf.drop(SCRAMBLED[1]).ge(0.75).all()
