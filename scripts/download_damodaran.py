"""Download the Damodaran (NYU Stern) US industry files used by the thesis into data/raw/.

File naming follows Damodaran's archive: the two-digit suffix is the DATA year, and the file is the
January update of the following year (e.g. archives/wacc24.xls = "1/25" update = 2024 data). The most
recent year is not archived yet; it is the current file in /pc/datasets/ and is saved with that year's
suffix (e.g. datasets/wacc.xls -> data/raw/wacc25.xls). The notebook reads the year from each file's
internal "Date updated" stamp where present, so a mislabelled newest file is still dated correctly.

Usage:
    python scripts/download_damodaran.py               # 1999 .. 2025
    python scripts/download_damodaran.py --last 2026   # once a newer update is published

If a download fails (the site occasionally blocks scripted requests), download the file by hand from
https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html (Firefox/Edge work more reliably
than Chrome there) and save it under data/raw/ with the name shown in the failure list.
"""
import argparse
import time
from pathlib import Path

import requests

ARCHIVE = "https://pages.stern.nyu.edu/~adamodar/pc/archives/{token}{yy:02d}.xls"
CURRENT = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/{token}.xls"
TOKENS = ["divfund", "divfcfe", "wacc", "capex"]
HEADERS = {"User-Agent": "Mozilla/5.0 (thesis replication script)"}


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    # A missing archive file can come back as an HTML error page with status 200, so check the bytes:
    # legacy .xls files are OLE2 documents starting with D0 CF 11 E0.
    if r.status_code == 200 and r.content[:4] == b"\xd0\xcf\x11\xe0":
        return r.content
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=1999)
    ap.add_argument("--last", type=int, default=2025, help="most recent data year (current file)")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    failed = []
    for token in TOKENS:
        for year in range(a.first, a.last + 1):
            yy = year % 100
            dest = out / f"{token}{yy:02d}.xls"
            if dest.exists() and not a.overwrite:
                continue
            urls = [ARCHIVE.format(token=token, yy=yy)]
            if year == a.last:                      # newest year lives in /datasets/ until archived
                urls.append(CURRENT.format(token=token))
            data = None
            for url in urls:
                try:
                    data = fetch(url)
                except requests.RequestException as e:
                    print(f"  ! {url}: {e}")
                if data:
                    dest.write_bytes(data)
                    print(f"ok  {dest.name:14s} <- {url}")
                    break
            if not data:
                failed.append(dest.name)
            time.sleep(0.5)                         # be polite to the server

    n = len(list(out.glob("*.xls")))
    print(f"\n{n} .xls files in {out}/")
    if failed:
        print("Not downloaded (fetch these by hand):", ", ".join(failed))


if __name__ == "__main__":
    main()
