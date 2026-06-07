"""Shared helpers for the official-site provider."""
from __future__ import annotations

import html as html_mod
import os
import re
import sys

from bs4 import NavigableString, Tag

from optcg.consts import LANGUAGES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
SERIES_MAP_FILE = os.path.join(BASE_DIR, "series_map.yaml")


def _print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def _sanitize(name: str) -> str:
    return re.sub(r"\W+", "", name)


# -- Language helpers -------------------------------------------------------

def _lang_info(lang: str) -> dict:
    return LANGUAGES[lang]


def _site_type(lang: str) -> str:
    return _lang_info(lang).get("site_type", "standard")


def _base_url(lang: str) -> str:
    return _lang_info(lang)["base_url"]


def _cardlist_url(lang: str) -> str:
    if _site_type(lang) == "kr":
        return f"{_base_url(lang)}/cardlist.do"
    return f"{_base_url(lang)}/cardlist/"


def _series_url(lang: str, series_number: int) -> str:
    return f"{_cardlist_url(lang)}?series={series_number}"


def _image_base_url(lang: str) -> str:
    return f"{_base_url(lang)}/images/cardlist/card/"


def _is_standard(lang: str) -> bool:
    return _site_type(lang) == "standard"


def _is_kr(lang: str) -> bool:
    return _site_type(lang) == "kr"


def _is_cn(lang: str) -> bool:
    return _site_type(lang) == "cn"


# -- HTML text extraction ---------------------------------------------------

def _text(el, class_name: str) -> str:
    """Extract the value text from a ``<div class="...">`` card field.

    Standard site divs have ``<h3>Label</h3> value`` structure; we skip the
    ``<h3>`` to return only the value portion.
    """
    tag = el.find("div", class_=class_name)
    if not tag:
        return "N/A"
    parts: list[str] = []
    for child in tag.children:
        if isinstance(child, Tag) and child.name == "h3":
            continue
        if isinstance(child, NavigableString):
            t = child.strip()
        else:
            t = child.get_text(" ", strip=True)
        if t:
            parts.append(t)
    text = " ".join(parts).strip()
    return text if text else "N/A"


def _p_text(el, class_name: str) -> str:
    """Extract direct text from a ``<p class="...">`` inside *el*.

    The Korean site nests ``<p>`` tags inside each other so we only take the
    text node that belongs directly to the matching ``<p>``, not its children.
    """
    tag = el.find("p", class_=class_name)
    if not tag:
        return "N/A"
    text = "".join(
        part.strip() for part in tag.children
        if isinstance(part, NavigableString)
    ).strip()
    return text if text else "N/A"
