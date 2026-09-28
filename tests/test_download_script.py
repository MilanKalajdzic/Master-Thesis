"""scripts/download_damodaran.py against a fake server (no network)."""
import importlib.util
import sys
import types

import pytest

from tests.conftest import REPO

OLE, ZIP = b"\xd0\xcf\x11\xe0" + b"x" * 10, b"PK\x03\x04" + b"y" * 10


@pytest.fixture
def dl(monkeypatch):
    spec = importlib.util.spec_from_file_location("download_damodaran", REPO / "scripts" / "download_damodaran.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    return mod


def fake_server(calls):
    def get(url, headers=None, timeout=None):
        calls.append(url)
        r = types.SimpleNamespace(status_code=200, content=b"<html>not found</html>")   # missing files come back as HTML
        name = url.rsplit("/", 1)[1]
        if "archives" in url:
            if name == "dbtfund99.xls":
                r.content = OLE
            elif name in ("dbtfund00.xlsx", "dbtfund01.xlsx"):
                r.content = ZIP
            elif name == "dbtfund01.xls":
                raise __import__("requests").ConnectionError("boom")
        elif name == "dbtfund.xls":
            r.status_code = 404
        elif name == "dbtfund.xlsx":
            r.content = ZIP
        return r
    return get


def run(dl, monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["download_damodaran.py", *args])
    dl.main()


def test_downloads_xls_and_xlsx_and_falls_back_to_the_current_file(dl, monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(dl.requests, "get", fake_server(calls))
    run(dl, monkeypatch, "--tokens", "dbtfund", "--first", "1999", "--last", "2002", "--out", str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dbtfund00.xlsx", "dbtfund01.xlsx", "dbtfund02.xlsx",
                                                          "dbtfund99.xls"]
    assert (tmp_path / "dbtfund99.xls").read_bytes() == OLE
    assert "boom" in capsys.readouterr().out                      # a failed request is reported, then .xlsx tried

    calls.clear()
    run(dl, monkeypatch, "--tokens", "dbtfund", "--first", "1999", "--last", "2002", "--out", str(tmp_path))
    assert calls == []                                            # existing files are skipped


def test_overwrite_replaces_a_copy_with_the_other_extension(dl, monkeypatch, tmp_path):
    (tmp_path / "dbtfund00.xls").write_bytes(OLE)
    monkeypatch.setattr(dl.requests, "get", fake_server([]))
    run(dl, monkeypatch, "--tokens", "dbtfund", "--first", "2000", "--last", "2000", "--out", str(tmp_path), "--overwrite")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dbtfund00.xlsx"]


def test_missing_files_are_listed(dl, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(dl.requests, "get", lambda *a, **k: types.SimpleNamespace(status_code=404, content=b""))
    run(dl, monkeypatch, "--tokens", "wacc", "--first", "2010", "--last", "2011", "--out", str(tmp_path))
    assert "wacc10.xls, wacc11.xls" in capsys.readouterr().out
    assert not any(tmp_path.iterdir())


def test_unknown_token_is_rejected(dl, monkeypatch):
    with pytest.raises(SystemExit):
        run(dl, monkeypatch, "--tokens", "bogus")
