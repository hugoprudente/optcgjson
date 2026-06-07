#!/usr/bin/env python3
"""One-time script to download HTML fixtures for tests.

Run from the repo root:
    python tests/download_fixtures.py
"""
import os
import sys
import time
import re
import zlib
import urllib.parse

import requests
from bs4 import BeautifulSoup

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
STANDARD_DIR = os.path.join(FIXTURES_DIR, "standard")
KR_DIR = os.path.join(FIXTURES_DIR, "kr")
DISCOVERY_DIR = os.path.join(FIXTURES_DIR, "discovery")

TARGET_SETS = ["OP11", "ST07", "PRB01", "EB02", "OP15"]

STANDARD_LANGS = {
    "en":      "https://asia-en.onepiece-cardgame.com",
    "ja":      "https://www.onepiece-cardgame.com",
    "fr":      "https://fr.onepiece-cardgame.com",
    "th":      "https://asia-th.onepiece-cardgame.com",
    "zh-Hant": "https://asia-tc.onepiece-cardgame.com",
    "en-na":   "https://en.onepiece-cardgame.com",
}

KR_SETS = ["OP11", "ST07", "EB02"]


def download(url: str, path: str) -> bool:
    if os.path.exists(path):
        print(f"  SKIP {path} (exists)")
        return True
    print(f"  GET  {url}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  FAIL {e}")
        return False
    with open(path, "wb") as f:
        f.write(resp.content)
    print(f"  SAVE {path} ({len(resp.content)} bytes)")
    time.sleep(0.3)
    return True


def discover_standard(base_url: str) -> dict[str, int]:
    """Return {set_code: series_id} for a standard site."""
    url = f"{base_url}/cardlist/"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    select = soup.find("select", attrs={"name": "series"})
    if not select:
        return {}
    result = {}
    for opt in select.find_all("option"):
        raw_val = (opt.get("value") or "").strip()
        if not raw_val.isdigit():
            continue
        label = opt.get_text(" ", strip=True)
        label = re.sub(r"<[^>]+>", "", label).strip()
        m = re.search(r"[\[【]([A-Z0-9\-]+)[\]】]", label)
        if m:
            code = m.group(1).replace("-", "")
        else:
            code = re.sub(r"\W+", "", label)
        result[code] = int(raw_val)
    return result


def discover_kr() -> dict[str, tuple[int, str]]:
    """Return {set_code: (synthetic_id, raw_option_value)} for Korean site."""
    url = "https://onepiece-cardgame.kr/cardlist.do"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    select = None
    for sel in soup.find_all("select"):
        opts = sel.find_all("option")
        if any(re.search(r"\[OPK-", o.get("value", "")) for o in opts):
            select = sel
            break
    if not select:
        return {}
    prefix_map = {"OPK": "OP", "STK": "ST", "EBK": "EB", "PRBK": "PRB"}
    result = {}
    for opt in select.find_all("option"):
        raw_val = (opt.get("value") or "").strip()
        if not raw_val or raw_val == "all":
            continue
        m = re.search(r"\[(OPK|STK|EBK|PRBK|[A-Z0-9]+)-?(\d+)\]", raw_val)
        if not m:
            continue
        std_prefix = prefix_map.get(m.group(1), m.group(1))
        code = f"{std_prefix}{m.group(2)}"
        syn_id = zlib.crc32(raw_val.encode("utf-8")) & 0x7FFFFFFF
        result[code] = (syn_id, raw_val)
    return result


def main():
    os.makedirs(STANDARD_DIR, exist_ok=True)
    os.makedirs(KR_DIR, exist_ok=True)
    os.makedirs(DISCOVERY_DIR, exist_ok=True)

    # -- Discovery pages --
    print("\n=== Discovery pages ===")
    download("https://asia-en.onepiece-cardgame.com/cardlist/",
             os.path.join(DISCOVERY_DIR, "en_cardlist.html"))
    download("https://onepiece-cardgame.kr/cardlist.do",
             os.path.join(DISCOVERY_DIR, "ko_cardlist.html"))

    # -- Standard fixtures --
    print("\n=== Standard language fixtures ===")
    for lang, base_url in STANDARD_LANGS.items():
        print(f"\n[{lang}] Discovering series from {base_url}...")
        try:
            code_to_id = discover_standard(base_url)
        except Exception as e:
            print(f"[{lang}] Discovery failed: {e}")
            continue
        print(f"[{lang}] Found {len(code_to_id)} series")

        for set_code in TARGET_SETS:
            sid = code_to_id.get(set_code)
            if sid is None:
                print(f"  [{lang}] {set_code}: not found, skipping")
                continue
            url = f"{base_url}/cardlist/?series={sid}"
            path = os.path.join(STANDARD_DIR, f"{lang}_{set_code}.html")
            download(url, path)

    # -- Korean fixtures --
    print("\n=== Korean fixtures ===")
    print("[ko] Discovering series...")
    try:
        kr_map = discover_kr()
    except Exception as e:
        print(f"[ko] Discovery failed: {e}")
        kr_map = {}
    print(f"[ko] Found {len(kr_map)} series")

    for set_code in KR_SETS:
        entry = kr_map.get(set_code)
        if entry is None:
            print(f"  [ko] {set_code}: not found, skipping")
            continue
        _, raw_val = entry
        encoded = urllib.parse.quote(raw_val)
        page = 0
        while True:
            url = (f"https://onepiece-cardgame.kr/cardlist.do"
                   f"?page={page}&size=20&series={encoded}"
                   f"&freewords=&categories=&colors=&illustrations=&blockIcons=")
            path = os.path.join(KR_DIR, f"ko_{set_code}_page{page}.html")
            if not download(url, path):
                break
            with open(path, "rb") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            card_list = soup.find("div", class_="card_sch_list")
            items = card_list.find_all("button", class_="item") if card_list else []
            print(f"    page {page}: {len(items)} cards")
            if len(items) < 20:
                break
            page += 1
            time.sleep(0.5)

    print("\n=== Done ===")
    total = sum(len(os.listdir(d)) for d in [STANDARD_DIR, KR_DIR, DISCOVERY_DIR]
                if os.path.isdir(d))
    print(f"Total fixture files: {total}")


if __name__ == "__main__":
    main()
