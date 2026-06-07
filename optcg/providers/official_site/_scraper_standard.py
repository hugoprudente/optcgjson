"""Standard-site scraper (all ``*.onepiece-cardgame.com`` subdomains)."""
from __future__ import annotations

import datetime

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from optcg.consts import PRIMARY_LANG
from optcg.providers.official_site._helpers import (
    _image_base_url, _print, _series_url, _text,
)


def scrape_series_standard(
    series_number: int,
    lang: str = PRIMARY_LANG,
    series_to_set_code: dict[int, str] | None = None,
) -> dict | None:
    """Fetch and parse a standard card-list page."""
    url = _series_url(lang, series_number)
    _print(f"[{lang}] Scraping {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        _print(f"[{lang}] Failed to retrieve series {series_number}: {exc}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    cards = parse_cards_standard(soup, lang)

    if not cards:
        _print(f"[{lang}] No cards found for series {series_number}")
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
            "language": lang,
        },
        "data": {
            "code": set_code,
            "cards": cards,
        },
    }


def parse_cards_standard(soup: BeautifulSoup, lang: str) -> list[dict]:
    """Pure parser: extract raw card dicts from a standard card-list page.

    This is the function tests call directly with fixture HTML.
    """
    card_elements = soup.find_all("dl", class_="modalCol")
    img_base = _image_base_url(lang)
    cards: list[dict] = []

    for el in card_elements:
        card_id = el.get("id", "N/A")

        info_col = el.find("div", class_="infoCol")
        if info_col:
            parts = info_col.text.split("|")
            card_number = parts[0].strip() if len(parts) > 0 else "N/A"
            card_type = parts[1].strip() if len(parts) > 1 else "N/A"
            card_class = parts[2].strip() if len(parts) > 2 else "N/A"
        else:
            card_number = card_type = card_class = "N/A"

        card_name = _text(el, "cardName")
        cost = _text(el, "cost")

        attr_div = el.find("div", class_="attribute")
        attribute_text = "N/A"
        if attr_div:
            i_tag = attr_div.find("i")
            if i_tag:
                attribute_text = i_tag.text.strip() or "N/A"

        power = _text(el, "power")
        counter = _text(el, "counter")
        color = _text(el, "color")
        feature = _text(el, "feature")

        block_div = el.find("div", class_="block")
        if block_div:
            block_parts: list[str] = []
            for child in block_div.children:
                if isinstance(child, Tag) and child.name == "h3":
                    continue
                if isinstance(child, NavigableString):
                    t = child.strip()
                else:
                    t = child.get_text(" ", strip=True)
                if t:
                    block_parts.append(t)
            block_icon = " ".join(block_parts).strip() or "N/A"
        else:
            block_icon = "N/A"

        effect = _text(el, "text")
        trigger = _text(el, "trigger")
        card_set = _text(el, "getInfo")
        image_url = f"{img_base}{card_id}.png"

        cards.append({
            "id": card_id,
            "number": card_number,
            "type": card_type,
            "class": card_class,
            "name": card_name,
            "cost": cost,
            "attribute": [] if attribute_text == "N/A" else attribute_text.split("/"),
            "trigger": trigger,
            "power": power,
            "counter": counter,
            "color": color.split("/") if color != "N/A" else [],
            "feature": feature.split("/") if feature != "N/A" else [],
            "block_icon": block_icon,
            "effect": effect,
            "card_set": card_set,
            "image_url": image_url,
        })

    return cards
