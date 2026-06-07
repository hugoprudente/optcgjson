"""Korean-site scraper (onepiece-cardgame.kr)."""
from __future__ import annotations

import datetime
import json
import os
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

from optcg.providers.official_site._helpers import BASE_DIR, _p_text, _print

_PARALLEL_SUFFIX_RE = re.compile(r"_[pP]\d*$")

_KR_SERIES_VALUE_CACHE: dict[int, str] = {}
_KR_CACHE_FILE = os.path.join(BASE_DIR, ".kr_series_cache.json")


def _save_kr_cache() -> None:
    with open(_KR_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in _KR_SERIES_VALUE_CACHE.items()}, f,
                  ensure_ascii=False, indent=2)


def _load_kr_cache() -> None:
    if not os.path.isfile(_KR_CACHE_FILE):
        return
    try:
        with open(_KR_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            _KR_SERIES_VALUE_CACHE[int(k)] = v
    except (OSError, json.JSONDecodeError, ValueError):
        pass


def _ensure_kr_cache() -> None:
    if _KR_SERIES_VALUE_CACHE:
        return
    _load_kr_cache()
    if _KR_SERIES_VALUE_CACHE:
        return
    _print("[ko] Populating series cache via discovery...")
    from optcg.providers.official_site._discovery import _discover_series_kr
    _discover_series_kr()


def scrape_series_kr(
    series_number: int,
    series_to_set_code: dict[int, str] | None = None,
) -> dict | None:
    """Fetch all pages for a Korean series and return a raw set dict."""
    _ensure_kr_cache()
    series_val = _KR_SERIES_VALUE_CACHE.get(series_number)
    if series_val is None:
        _print(f"[ko] No cached option-value for synthetic ID {series_number}; "
               "run refresh-list --lang ko first.")
        return None

    encoded = urllib.parse.quote(series_val)
    page_size = 20
    all_items = []

    for page in range(200):
        url = (f"https://onepiece-cardgame.kr/cardlist.do"
               f"?page={page}&size={page_size}&series={encoded}"
               f"&freewords=&categories=&colors=&illustrations=&blockIcons=")
        if page == 0:
            _print(f"[ko] Scraping {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            _print(f"[ko] Failed to retrieve series page {page}: {exc}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        card_list = soup.find("div", class_="card_sch_list")
        if not card_list:
            break
        items = card_list.find_all("button", class_="item")
        if not items:
            break

        all_items.extend(items)
        _print(f"[ko]   page {page}: {len(items)} cards (total so far: {len(all_items)})")

        if len(items) < page_size:
            break
        time.sleep(0.5)

    if not all_items:
        _print(f"[ko] No card items found for series {series_number}")
        return None

    cards = parse_cards_kr(all_items)

    if not cards:
        _print(f"[ko] No cards parsed for series {series_number}")
        return None

    if series_to_set_code and series_number in series_to_set_code:
        set_code = series_to_set_code[series_number]
    else:
        first = cards[0]["number"]
        set_code = first.split("-")[0] if "-" in first else first

    return {
        "meta": {
            "date": datetime.date.today().isoformat(),
            "version": "1.0.0",
            "set": series_number,
            "language": "ko",
        },
        "data": {
            "code": set_code,
            "cards": cards,
        },
    }


def parse_cards_kr(items: list) -> list[dict]:
    """Pure parser: extract raw card dicts from Korean ``<button class="item">`` elements.

    This is the function tests call directly with fixture HTML elements.
    """
    cards: list[dict] = []
    for el in items:
        card_number = _p_text(el, "cardNumber")
        card_name = _p_text(el, "cardName")
        card_type = _p_text(el, "cardType") or "N/A"
        rarity = _p_text(el, "rarity") or "N/A"
        color = _p_text(el, "cardColor") or "N/A"
        power = _p_text(el, "power") or "N/A"
        counter = _p_text(el, "cardCounter") or "N/A"
        feature = _p_text(el, "cardPoint") or "N/A"
        attribute = _p_text(el, "cardAttr") or "N/A"
        effect = _p_text(el, "cardText") or "N/A"
        trigger = _p_text(el, "cardTrigger") or "N/A"
        block_icon = _p_text(el, "blockNumber") or "N/A"
        life = _p_text(el, "life") or "N/A"
        card_set = _p_text(el, "cardGet") or "N/A"

        img_tag = el.find("img", class_="image")
        image_url = (img_tag.get("src") or "N/A") if img_tag else "N/A"

        cost = life

        card_id = card_number
        clean_number = _PARALLEL_SUFFIX_RE.sub("", card_number)

        colors = [c.strip() for c in color.split(",") if c.strip()] if color != "N/A" else []
        features = [f.strip() for f in feature.split("/") if f.strip()] if feature != "N/A" else []

        cards.append({
            "id": card_id,
            "number": clean_number,
            "type": rarity,
            "class": card_type,
            "name": card_name,
            "cost": cost,
            "attribute": [] if attribute == "N/A" else [a.strip() for a in attribute.split("/") if a.strip()],
            "trigger": trigger,
            "power": power,
            "counter": counter,
            "color": colors,
            "feature": features,
            "block_icon": block_icon,
            "effect": effect,
            "card_set": card_set,
            "image_url": image_url,
        })

    return cards
