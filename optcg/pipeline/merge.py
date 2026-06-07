"""Merge foreign-language card data onto primary-language cards."""

from __future__ import annotations

import sys

from optcg.consts import LANGUAGES, PRIMARY_LANG
from optcg.models.cards import TRANSLATABLE_FIELDS, new_foreign_entry


def merge_foreign_data(
    primary_cards: list[dict],
    foreign_sets: dict[str, list[dict]],
) -> list[dict]:
    """Add ``foreignData`` and ``languages`` to each primary card.

    Parameters
    ----------
    primary_cards:
        List of normalised card dicts in the primary language.
    foreign_sets:
        ``{lang_code: [normalised_card, ...]}`` for every non-primary
        language that has been scraped.

    Returns the *primary_cards* list mutated in place (for convenience).
    """
    primary_name = LANGUAGES[PRIMARY_LANG]["name"]

    # Build per-language indexes keyed by card number for O(1) lookup.
    indexes: dict[str, dict[str, dict]] = {}
    for lang, cards in foreign_sets.items():
        idx: dict[str, dict] = {}
        for card in cards:
            num = card.get("number")
            if num:
                idx[num] = card
        indexes[lang] = idx

    for card in primary_cards:
        number = card.get("number")
        available = [primary_name]
        foreign: list[dict] = []

        for lang, idx in indexes.items():
            foreign_card = idx.get(number)
            if foreign_card is None:
                continue
            lang_display = LANGUAGES.get(lang, {}).get("name", lang)
            available.append(lang_display)
            foreign.append(new_foreign_entry(lang_display, foreign_card))

        card["languages"] = available
        card["foreign_data"] = foreign if foreign else None

    return primary_cards
