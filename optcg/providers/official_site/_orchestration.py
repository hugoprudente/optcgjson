"""High-level orchestration: dispatch, write, refresh."""
from __future__ import annotations

import html as html_mod
import json
import os
import re

from optcg.consts import LANGUAGES, PRIMARY_LANG
from optcg.providers.official_site._helpers import BASE_DIR, _is_cn, _is_kr, _print
from optcg.providers.official_site._yaml_map import (
    build_series_to_set_code,
    load_series_map,
    series_ids_for_lang,
    write_series_map,
)
from optcg.providers.official_site._discovery import discover_series_from_site
from optcg.providers.official_site._scraper_standard import scrape_series_standard
from optcg.providers.official_site._scraper_kr import scrape_series_kr


def scrape_series(
    series_number: int,
    lang: str = PRIMARY_LANG,
    series_to_set_code: dict[int, str] | None = None,
) -> dict | None:
    """Scrape a single series page -- dispatches by site_type."""
    if _is_cn(lang):
        _print(f"[{lang}] Chinese Simplified (.cn) is a JS-rendered SPA; scraping not supported.")
        return None
    if _is_kr(lang):
        return scrape_series_kr(series_number, series_to_set_code)
    return scrape_series_standard(series_number, lang, series_to_set_code)


def write_raw_set(set_info: dict, lang: str) -> str:
    """Write a raw set dict to ``sets/{lang}/{CODE}.json`` and return the path."""
    code = set_info["data"]["code"]
    out_dir = os.path.join(BASE_DIR, "sets", lang)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(set_info, f, ensure_ascii=False, indent=4)
    _print(f"[{lang}] Wrote {path}")
    return path


def scrape_sets(
    series_map: dict[str, dict],
    lang: str = PRIMARY_LANG,
    set_codes: list[str] | None = None,
) -> list[str]:
    """Scrape all (or selected) sets for a language. Returns file paths written."""
    if _is_cn(lang):
        _print(f"[{lang}] Chinese Simplified (.cn) is a JS-rendered SPA; scraping not supported.")
        return []

    s2c = build_series_to_set_code(series_map, lang)
    all_ids = series_ids_for_lang(series_map, lang)

    if set_codes:
        wanted: set[int] = set()
        for code in set_codes:
            info = series_map.get(code, {})
            series = info.get("series", {})
            if isinstance(series, dict):
                for sid in series.get(lang, []):
                    wanted.add(sid)
        all_ids = sorted(set(all_ids) & wanted) if wanted else []

    if not all_ids:
        _print(f"[{lang}] No series IDs to scrape.")
        return []

    paths: list[str] = []
    for sid in all_ids:
        result = scrape_series(sid, lang=lang, series_to_set_code=s2c)
        if result:
            p = write_raw_set(result, lang)
            paths.append(p)

    _print(f"[{lang}] Scraped {len(paths)} sets.")
    return paths


def refresh_series_map(langs: list[str] | None = None) -> None:
    """Rebuild ``series_map.yaml`` from live discovery."""
    if langs is None:
        langs = [k for k in LANGUAGES if not _is_cn(k)]

    old_map = load_series_map()
    new_map: dict[str, dict] = {}

    for lang in langs:
        if lang not in LANGUAGES:
            _print(f"Skipping unknown language: {lang}")
            continue
        if _is_cn(lang):
            _print(f"[{lang}] Skipping -- JS-rendered SPA, discovery not supported.")
            continue

        entries = discover_series_from_site(lang)
        for set_code, series_id in entries:
            if set_code not in new_map:
                old_name = old_map.get(set_code, {}).get("name", "")
                new_map[set_code] = {"name": old_name, "series": {}}
            series_dict = new_map[set_code]["series"]
            series_dict.setdefault(lang, [])
            if series_id not in series_dict[lang]:
                series_dict[lang].append(series_id)

    for code, info in new_map.items():
        if not info.get("name"):
            info["name"] = code

    _patch_names_from_json(new_map)
    write_series_map(new_map)
    _print(f"series_map.yaml rewritten with {len(new_map)} sets across {len(langs)} language(s).")


def _patch_names_from_json(series_map: dict[str, dict]) -> None:
    sets_dir = os.path.join(BASE_DIR, "sets", PRIMARY_LANG)
    if not os.path.isdir(sets_dir):
        sets_dir = os.path.join(BASE_DIR, "sets")
    if not os.path.isdir(sets_dir):
        return

    for filename in os.listdir(sets_dir):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(sets_dir, filename), "r", encoding="utf-8") as jf:
                payload = json.load(jf)
        except (OSError, json.JSONDecodeError):
            continue

        data = payload.get("data") or {}
        code = data.get("code")
        cards = data.get("cards") or []
        if not code or not cards:
            continue
        label = (cards[0].get("card_set") or "").strip()
        if not label:
            continue
        label = html_mod.unescape(re.sub(r"<[^>]+>", "", label)).strip()

        entry = series_map.get(code)
        if entry and not entry.get("name"):
            entry["name"] = label
