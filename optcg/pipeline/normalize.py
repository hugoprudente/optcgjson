"""Normalize raw scraped card dicts into the standardised internal schema."""

from __future__ import annotations

import re

from optcg.consts import clean_sentinel, set_type_for_code

# Class strings that identify a Leader card across the scraped languages.
# The standard sites emit "LEADER"; the Korean site emits "리더".
# The scraped ``cost`` field shares its HTML cell with the Life value on
# Leader cards, so on Leaders we move that value into a dedicated ``life``
# field and leave ``cost`` null.
LEADER_CLASSES = frozenset({"LEADER", "리더"})


def normalize_card(raw: dict) -> dict:
    """Transform a single raw card dict (from the scraper) into the internal
    normalised format used throughout the pipeline.

    Raw fields are snake_case; internal dict uses the same snake_case keys that
    ``models.cards`` defines.
    """
    number = (raw.get("number") or raw.get("id") or "").strip()
    card_id = (raw.get("id") or number).strip()

    name = (raw.get("name") or "").strip()
    rarity = (raw.get("type") or "").strip()
    card_class = (raw.get("class") or "").strip()

    raw_cost = _clean(raw.get("cost"))
    if card_class.upper() in LEADER_CLASSES:
        cost = None
        life = raw_cost
    else:
        cost = raw_cost
        life = None
    power = _clean(raw.get("power"))
    counter = _clean(raw.get("counter"))
    block_icon = _clean(raw.get("block_icon"))
    effect = _clean(raw.get("effect"))
    trigger = _clean(raw.get("trigger"))
    image_url = (raw.get("image_url") or "").strip() or None

    attribute = _norm_list(raw.get("attribute"))
    color = _norm_list(raw.get("color"))
    feature = _norm_list(raw.get("feature"))

    is_parallel = _detect_parallel(card_id, name)

    return {
        "id": card_id,
        "number": number,
        "name": name or None,
        "rarity": rarity or None,
        "card_class": card_class or None,
        "cost": cost,
        "life": life,
        "attribute": attribute or None,
        "power": power,
        "counter": counter,
        "color": color or None,
        "feature": feature or None,
        "trigger": trigger,
        "block_icon": block_icon,
        "effect": effect,
        "image_url": image_url,
        "is_parallel": is_parallel,
        "languages": None,
        "foreign_data": None,
    }


def _clean(value) -> str | None:
    """Strip and sentinel-clean a scalar value."""
    if value is None:
        return None
    if isinstance(value, list):
        return None
    s = str(value).strip()
    return clean_sentinel(s)


def _norm_list(value) -> list[str] | None:
    """Normalise a list-valued field (attribute, color, feature).

    Accepts either a list or a ``/``-separated string.  Returns ``None`` when
    empty or sentinel.
    """
    if value is None:
        return None

    if isinstance(value, list):
        items = value
    else:
        s = str(value).strip()
        if clean_sentinel(s) is None:
            return None
        items = s.split("/")

    cleaned = [i.strip() for i in items if i.strip() and clean_sentinel(i.strip()) is not None]
    return cleaned if cleaned else None


_PARALLEL_RE = re.compile(r"_p\d*$", re.IGNORECASE)


def _detect_parallel(card_id: str, name: str) -> bool:
    """Heuristic: IDs ending in ``_p1``, ``_p2``, etc. are parallel art variants."""
    return bool(_PARALLEL_RE.search(card_id))
