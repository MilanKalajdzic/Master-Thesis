"""Download the Damodaran (NYU Stern) US industry files used by the thesis into data/raw/.

File naming follows Damodaran's archive: the two-digit suffix is the DATA year, and the file is the
January update of the following year (e.g. archives/wacc24.xls = "1/25" update = 2024 data). The most
recent year is not archived yet; it is the current file in /pc/datasets/ and is saved with that year's
suffix (e.g. datasets/wacc.xls -> data/raw/wacc25.xls). The notebook reads the year from each file's
internal "Date updated" stamp where present, so a mislabelled newest file is still dated correctly.

Some archive years are published as .xlsx instead of .xls; both are tried and the file is saved with the
extension the server actually delivered.

Usage:
    python scripts/download_damodaran.py                   # all datasets, 1999 .. 2025
    python scripts/download_damodaran.py --tokens dbtfund  # one dataset only
    python scripts/download_damodaran.py --last 2026       # once a newer update is published

If a download fails (the site occasionally blocks scripted requests), download the file by hand from
https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html (Firefox/Edge work more reliably
than Chrome there) and save it under data/raw/ with the name shown in the failure list.
"""
import argparse
import time
from pathlib import Path

import requests

ARCHIVE = "https://pages.stern.nyu.edu/~adamodar/pc/archives/{token}{yy:02d}{ext}"
CURRENT = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/{token}{ext}"
TOKENS = ["divfund", "divfcfe", "wacc", "capex", "dbtfund"]
EXTS = [".xls", ".xlsx"]
HEADERS = {"User-Agent": "Mozilla/5.0 (thesis replication script)"}
# A missing file can come back as an HTML error page with status 200, so check the leading bytes:
# legacy .xls files are OLE2 documents (D0 CF 11 E0), .xlsx files are ZIP archives (PK 03 04).
MAGIC = {".xls": b"\xd0\xcf\x11\xe0", ".xlsx": b"PK\x03\x04"}


def fetch(url, ext):
    r = requests.get(url, headers=HEADERS, timeout=60)
    if r.status_code == 200 and r.content[:4] == MAGIC[ext]:
        return r.content
    return None


def existing(out, token, yy):
    """Already downloaded under either extension?"""
    return [out / f"{token}{yy:02d}{ext}" for ext in EXTS if (out / f"{token}{yy:02d}{ext}").exists()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=1999)
    ap.add_argument("--last", type=int, default=2025, help="most recent data year (current file)")
    ap.add_argument("--tokens", nargs="+", default=TOKENS, choices=TOKENS, metavar="TOKEN",
                    help=f"datasets to download (default: all of {' '.join(TOKENS)})")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    failed = []
    for token in a.tokens:
        for year in range(a.first, a.last + 1):
            yy = year % 100
            if existing(out, token, yy) and not a.overwrite:
                continue
            tries = [(ARCHIVE.format(token=token, yy=yy, ext=ext), ext) for ext in EXTS]
            if year == a.last:                      # newest year lives in /datasets/ until archived
                tries += [(CURRENT.format(token=token, ext=ext), ext) for ext in EXTS]
            data = None
            for url, ext in tries:
                try:
                    data = fetch(url, ext)
                except requests.RequestException as e:
                    print(f"  ! {url}: {e}")
                if data:
                    dest = out / f"{token}{yy:02d}{ext}"
                    for old in existing(out, token, yy):   # --overwrite: drop a copy with the other extension
                        if old != dest:
                            old.unlink()
                    dest.write_bytes(data)
                    print(f"ok  {dest.name:15s} <- {url}")
                    break
            if not data:
                failed.append(f"{token}{yy:02d}.xls")
            time.sleep(0.5)                         # be polite to the server

    for token in a.tokens:
        n = len([f for f in out.glob(f"{token}*.xls*") if f.suffix in EXTS])
        print(f"{token:8s}: {n} files in {out}/")
    if failed:
        print("Not downloaded (fetch these by hand, .xls or .xlsx):", ", ".join(failed))


if __name__ == "__main__":
    main()
