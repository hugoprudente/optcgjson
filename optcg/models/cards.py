"""Card dict schema and serialisation helpers."""

from __future__ import annotations

from optcg.consts import clean_sentinel

# Fields that are translated across languages and stored in foreignData.
TRANSLATABLE_FIELDS = ("name", "effect", "trigger", "attribute", "feature")


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# Ordered list of output keys (snake_case internally, camelCase in JSON).
CARD_FIELDS = [
    "id",
    "number",
    "name",
    "rarity",
    "card_class",
    "cost",
    "attribute",
    "power",
    "counter",
    "color",
    "feature",
    "trigger",
    "block_icon",
    "effect",
    "image_url",
    "is_parallel",
    "languages",
    "foreign_data",
]


def new_card(**kwargs) -> dict:
    """Create a card dict with all expected keys (missing ones default to None)."""
    card: dict = {}
    for field in CARD_FIELDS:
        card[field] = kwargs.get(field)
    return card


def card_to_dict(card: dict) -> dict:
    """Serialise a card dict to camelCase JSON-ready dict."""
    out: dict = {}
    for field in CARD_FIELDS:
        value = card.get(field)
        key = _to_camel(field)
        out[key] = value
    return out


def new_foreign_entry(language: str, card: dict) -> dict:
    """Build a foreignData entry from a normalised foreign-language card."""
    entry: dict = {"language": language}
    for field in TRANSLATABLE_FIELDS:
        entry[field] = card.get(field)
    return entry
