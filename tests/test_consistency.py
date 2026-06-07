"""Cross-language consistency tests.

Verify that all languages produce the same base card numbers for a given set,
and that field semantics are aligned so the merge pipeline works correctly.
"""
from __future__ import annotations

import re
import pytest
from tests.conftest import STANDARD_FIXTURES, kr_items_from_pages
from optcg.providers.official_site import parse_cards_standard, parse_cards_kr


def _base_numbers(cards: list[dict]) -> set[str]:
    """Extract base card numbers (stripping parallel suffixes)."""
    nums = set()
    for c in cards:
        num = c["number"]
        # Strip lowercase _p or uppercase _P suffixes
        num = re.sub(r"_[pP]\d*$", "", num)
        nums.add(num)
    return nums


class TestCrossLanguageOP11:
    """Languages for OP11 should produce the same base card numbers.

    Some regional sites (en-na, fr) include extra cross-set promos; we verify
    that EN's base set is a *subset* of every other language and that any
    extras are from other sets (non-OP11 prefix).
    """

    STANDARD_OP11 = [p for p in STANDARD_FIXTURES if p[1] == "OP11"]

    @pytest.mark.parametrize("lang,set_code", STANDARD_OP11)
    def test_base_numbers_superset_of_en(self, load_standard, lang, set_code):
        if lang == "en":
            return
        en_soup = load_standard("en", "OP11")
        en_cards = parse_cards_standard(en_soup, "en")
        en_base = _base_numbers(en_cards)

        lang_soup = load_standard(lang, "OP11")
        lang_cards = parse_cards_standard(lang_soup, lang)
        lang_base = _base_numbers(lang_cards)

        missing = en_base - lang_base
        assert not missing, f"[{lang}] OP11 missing vs EN: {sorted(missing)}"

        extra = lang_base - en_base
        for num in extra:
            assert not num.startswith("OP11-"), (
                f"[{lang}] OP11 has extra OP11-prefixed card not in EN: {num}"
            )

    def test_ko_base_numbers_match_en(self, load_standard, load_kr_pages):
        en_soup = load_standard("en", "OP11")
        en_cards = parse_cards_standard(en_soup, "en")
        en_base = _base_numbers(en_cards)

        pages = load_kr_pages("OP11")
        items = kr_items_from_pages(pages)
        ko_cards = parse_cards_kr(items)
        ko_base = _base_numbers(ko_cards)

        missing = en_base - ko_base
        extra = ko_base - en_base
        assert not missing, f"[ko] OP11 missing vs EN: {sorted(missing)}"
        assert not extra, f"[ko] OP11 extra vs EN: {sorted(extra)}"


class TestFieldAlignment:
    """Fields that the merge uses must be semantically consistent."""

    STANDARD_OP11 = [p for p in STANDARD_FIXTURES if p[1] == "OP11"]

    @pytest.mark.parametrize("lang,set_code", STANDARD_OP11)
    def test_type_is_rarity_code(self, load_standard, lang, set_code):
        """type field must start with a known rarity code prefix. Some sites
        append localized text (e.g. 'SP CARD', 'SPカード', 'SP卡')."""
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        prefixes = ("L", "C", "UC", "R", "SR", "SEC", "SP", "P", "TR", "M")
        def _ok(t: str) -> bool:
            return any(t == p or t.startswith(p + " ") or
                       (t.startswith(p) and len(p) > 1)
                       for p in prefixes)
        bad = [(c["number"], c["type"]) for c in cards if not _ok(c["type"])]
        assert not bad, f"[{lang}] Cards with non-rarity type prefix: {bad[:5]}"

    @pytest.mark.parametrize("lang,set_code", STANDARD_OP11)
    def test_class_is_role(self, load_standard, lang, set_code):
        """class field must be a card role. Localized roles are accepted."""
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        valid = {
            "LEADER", "CHARACTER", "EVENT", "STAGE",
            "PERSONNAGE", "ÉVÉNEMENTS", "ÉVÈNEMENT", "ÉTAPE", "LIEU",
        }
        bad = [(c["number"], c["class"]) for c in cards if c["class"] not in valid]
        assert not bad, f"[{lang}] Cards with non-role class: {bad[:5]}"

    def test_ko_type_is_rarity_code(self, load_kr_pages):
        """After fix: KO type field must be a rarity code."""
        pages = load_kr_pages("OP11")
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        valid = {"L", "C", "UC", "R", "SR", "SEC", "SP", "P", "TR", "M"}
        bad = [(c["number"], c["type"]) for c in cards if c["type"] not in valid]
        assert not bad, f"[ko] Cards with non-rarity type: {bad[:5]}"
