"""Series discovery -- parse the card-list page dropdowns."""
from __future__ import annotations

import html as html_mod
import re
import zlib

import requests
from bs4 import BeautifulSoup

from optcg.providers.official_site._helpers import (
    _cardlist_url, _is_cn, _is_kr, _print, _sanitize,
)
from optcg.providers.official_site._scraper_kr import _KR_SERIES_VALUE_CACHE, _save_kr_cache

KR_PREFIX_MAP: dict[str, str] = {"OPK": "OP", "STK": "ST", "EBK": "EB", "PRBK": "PRB"}


def discover_series_from_site(lang: str) -> list[tuple[str, int]]:
    """Discover ``(set_code, series_id)`` pairs from the card-list page."""
    if _is_cn(lang):
        _print(f"[{lang}] Chinese Simplified (.cn) is a JS-rendered SPA; discovery not supported.")
        return []
    if _is_kr(lang):
        return _discover_series_kr()
    return _discover_series_standard(lang)


def _discover_series_standard(lang: str) -> list[tuple[str, int]]:
    """Standard sites: parse ``<select name="series">`` with numeric IDs."""
    url = _cardlist_url(lang)
    _print(f"[{lang}] Discovering series from {url}")
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        _print(f"[{lang}] Failed to reach {url}: {exc}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    return parse_discovery_standard(soup, lang)


def parse_discovery_standard(soup: BeautifulSoup, lang: str) -> list[tuple[str, int]]:
    """Pure parser: extract ``(set_code, series_id)`` from a standard discovery page."""
    select = soup.find("select", attrs={"name": "series"})
    if not select:
        return []

    results: list[tuple[str, int]] = []
    for opt in select.find_all("option"):
        raw_val = (opt.get("value") or "").strip()
        if not raw_val.isdigit():
            continue
        series_id = int(raw_val)
        label = html_mod.unescape(opt.get_text(" ", strip=True))
        label = re.sub(r"<[^>]+>", "", label).strip()

        m = re.search(r"[\[【]([A-Z0-9\-]+)[\]】]", label)
        if m:
            set_code = m.group(1).replace("-", "")
        else:
            set_code = _sanitize(label)

        results.append((set_code, series_id))
    return results


def _discover_series_kr() -> list[tuple[str, int]]:
    """Korean site: fetch and parse the discovery page."""
    url = "https://onepiece-cardgame.kr/cardlist.do"
    _print(f"[ko] Discovering series from {url}")
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        _print(f"[ko] Failed to reach {url}: {exc}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    results = parse_discovery_kr(soup)
    _save_kr_cache()
    return results


def parse_discovery_kr(soup: BeautifulSoup) -> list[tuple[str, int]]:
    """Pure parser: extract ``(set_code, synthetic_id)`` from the Korean discovery page."""
    select = None
    for sel in soup.find_all("select"):
        opts = sel.find_all("option")
        if any(re.search(r"\[OPK-", o.get("value", "")) for o in opts):
            select = sel
            break

    if not select:
        return []

    results: list[tuple[str, int]] = []
    for opt in select.find_all("option"):
        raw_val = (opt.get("value") or "").strip()
        if not raw_val or raw_val == "all":
            continue

        m = re.search(r"\[(OPK|STK|EBK|PRBK|[A-Z0-9]+)-?(\d+)\]", raw_val)
        if not m:
            continue

        kr_prefix = m.group(1)
        number = m.group(2)
        std_prefix = KR_PREFIX_MAP.get(kr_prefix, kr_prefix)
        set_code = f"{std_prefix}{number}"

        syn_id = zlib.crc32(raw_val.encode("utf-8")) & 0x7FFFFFFF
        results.append((set_code, syn_id))
        _KR_SERIES_VALUE_CACHE[syn_id] = raw_val

    return results
