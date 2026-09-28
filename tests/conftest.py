from pathlib import Path

import pandas as pd
import pytest

from paylev.damodaran import TOKENS, discover_sources, load_year
from paylev.synthetic import write_fake_damodaran

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def fake_dir(tmp_path_factory):
    """Fake Damodaran files for 1999-2025 in the three real layouts (see paylev/synthetic.py)."""
    folder = tmp_path_factory.mktemp("damodaran")
    write_fake_damodaran(folder)
    return folder


@pytest.fixture(scope="session")
def sources(fake_dir):
    return {t: discover_sources(t, [fake_dir]) for t in TOKENS}


@pytest.fixture(scope="session")
def raw(sources):
    """All years' rows merged across files, before any cleaning (like `raw` in the notebook)."""
    years = sorted(set(sources["divfund"]) & set(sources["wacc"]))
    return pd.concat([load_year(y, sources) for y in years], ignore_index=True)
