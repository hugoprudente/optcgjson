"""Lightweight schema validation for normalised card dicts."""

from __future__ import annotations


REQUIRED_FIELDS = ("id", "number", "name")
LIST_FIELDS = ("attribute", "color", "feature", "foreign_data", "languages")
OPTIONAL_STRING_FIELDS = (
    "rarity", "card_class", "cost", "life", "power", "counter",
    "block_icon", "effect", "trigger", "image_url",
)


def validate_card(card: dict, *, strict: bool = False) -> list[str]:
    """Return a list of validation error messages (empty means valid).

    When *strict* is True, also checks for recommended (but not mandatory)
    fields like ``rarity`` and ``color``.
    """
    errors: list[str] = []
    cid = card.get("id") or card.get("number") or "<unknown>"

    for field in REQUIRED_FIELDS:
        val = card.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"[{cid}] Missing required field '{field}'")

    for field in LIST_FIELDS:
        val = card.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"[{cid}] Field '{field}' should be a list, got {type(val).__name__}")

    if strict:
        if not card.get("rarity"):
            errors.append(f"[{cid}] Missing recommended field 'rarity'")
        if not card.get("color"):
            errors.append(f"[{cid}] Missing recommended field 'color'")

    return errors


def validate_set(s: dict) -> list[str]:
    """Return a list of validation error messages for a set dict."""
    errors: list[str] = []
    code = s.get("code") or "<unknown>"
    if not s.get("code"):
        errors.append("Missing required field 'code'")
    if not s.get("name"):
        errors.append(f"[{code}] Missing required field 'name'")
    cards = s.get("cards")
    if cards is None or not isinstance(cards, list):
        errors.append(f"[{code}] Field 'cards' must be a list")
    return errors
