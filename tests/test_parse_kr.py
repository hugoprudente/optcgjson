"""Tests for the Korean-site card parser."""
from __future__ import annotations

import pytest
from tests.conftest import kr_items_from_pages
from optcg.providers.official_site import parse_cards_kr

EXPECTED_COUNTS: dict[str, int] = {
    "OP11": 155,
    "ST07": 17,
    "EB02": 105,
}

REQUIRED_CARD_KEYS = {
    "id", "number", "type", "class", "name", "cost", "attribute",
    "trigger", "power", "counter", "color", "feature", "block_icon",
    "effect", "card_set", "image_url",
}


class TestKrCardCounts:

    @pytest.mark.parametrize("set_code", ["OP11", "ST07", "EB02"])
    def test_card_count(self, load_kr_pages, set_code):
        pages = load_kr_pages(set_code)
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        expected = EXPECTED_COUNTS[set_code]
        assert len(cards) == expected, (
            f"[ko] {set_code}: expected {expected} cards, got {len(cards)}"
        )


class TestKrFieldPopulation:

    @pytest.mark.parametrize("set_code", ["OP11", "ST07", "EB02"])
    def test_all_keys_present(self, load_kr_pages, set_code):
        pages = load_kr_pages(set_code)
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        for card in cards:
            missing = REQUIRED_CARD_KEYS - card.keys()
            assert not missing, f"[ko] {set_code} card {card.get('id')}: missing keys {missing}"

    @pytest.mark.parametrize("set_code", ["OP11"])
    def test_name_populated(self, load_kr_pages, set_code):
        pages = load_kr_pages(set_code)
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        for card in cards:
            assert card["name"] and card["name"] != "N/A", (
                f"[ko] {set_code} card {card['id']}: name is empty"
            )

    @pytest.mark.parametrize("set_code", ["OP11"])
    def test_number_format(self, load_kr_pages, set_code):
        pages = load_kr_pages(set_code)
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        for card in cards:
            num = card["number"]
            base = num.split("_")[0] if "_" in num else num
            assert "-" in base, f"[ko] card number '{num}' base has no dash"


class TestKrTypeClassSemantics:
    """After the fix, KO must match EN semantics: type=rarity, class=role.

    Currently broken: type=localized role, class=rarity code.
    This test documents the EXPECTED (correct) behavior.
    """

    def test_first_card_type_class(self, load_kr_pages):
        pages = load_kr_pages("OP11")
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        first = cards[0]
        # After fix: type should be rarity code, class should be role
        assert first["type"] == "L", (
            f"[ko] First card type should be 'L' (rarity), got '{first['type']}'"
        )
        assert first["class"] == "LEADER" or "리더" in first["class"], (
            f"[ko] First card class should be a role, got '{first['class']}'"
        )


class TestKrParallelCards:
    """Parallel cards: id has _P suffix, number must be clean (after fix)."""

    def test_parallel_number_is_clean(self, load_kr_pages):
        pages = load_kr_pages("OP11")
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        for card in cards:
            if "_P" in card["id"] or "_p" in card["id"]:
                assert "_P" not in card["number"] and "_p" not in card["number"], (
                    f"[ko] Parallel card {card['id']}: "
                    f"number '{card['number']}' should not contain _P suffix"
                )


class TestKrCostIsNumeric:

    def test_cost_numeric(self, load_kr_pages):
        pages = load_kr_pages("OP11")
        items = kr_items_from_pages(pages)
        cards = parse_cards_kr(items)
        for card in cards:
            cost = card["cost"]
            if cost == "N/A":
                continue
            assert cost.isdigit(), (
                f"[ko] Card {card['number']}: cost '{cost}' should be numeric"
            )
