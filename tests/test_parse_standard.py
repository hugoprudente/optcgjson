"""Tests for the standard-site card parser across all languages."""
from __future__ import annotations

import pytest
from tests.conftest import STANDARD_FIXTURES
from optcg.providers.official_site import parse_cards_standard

# Regional sites may include extra promos; key is (lang, set_code) for overrides.
BASE_EXPECTED_COUNTS: dict[str, int] = {
    "OP11": 155,
    "ST07": 17,
    "PRB01": 319,
    "EB02": 105,
    "OP15": 152,
}
COUNT_OVERRIDES: dict[tuple[str, str], int] = {
    ("en-na", "OP11"): 156,
    ("fr", "OP11"): 156,
}

STANDARD_LANGS = {"en", "ja", "fr", "th", "zh-Hant", "en-na"}

REQUIRED_CARD_KEYS = {
    "id", "number", "type", "class", "name", "cost", "attribute",
    "trigger", "power", "counter", "color", "feature", "block_icon",
    "effect", "card_set", "image_url",
}


def _expected_count(lang: str, set_code: str) -> int:
    return COUNT_OVERRIDES.get((lang, set_code), BASE_EXPECTED_COUNTS[set_code])


class TestCardCounts:
    """Every language must produce the expected card count for the set."""

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] in BASE_EXPECTED_COUNTS
    ])
    def test_card_count(self, load_standard, lang, set_code):
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        expected = _expected_count(lang, set_code)
        assert len(cards) == expected, (
            f"[{lang}] {set_code}: expected {expected} cards, got {len(cards)}"
        )


class TestFieldPopulation:
    """Every card must have all required keys with non-empty values for core fields."""

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] in BASE_EXPECTED_COUNTS
    ])
    def test_all_keys_present(self, load_standard, lang, set_code):
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        for card in cards:
            missing = REQUIRED_CARD_KEYS - card.keys()
            assert not missing, f"[{lang}] {set_code} card {card.get('id')}: missing keys {missing}"

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] in BASE_EXPECTED_COUNTS
    ])
    def test_name_populated(self, load_standard, lang, set_code):
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        for card in cards:
            assert card["name"] and card["name"] != "N/A", (
                f"[{lang}] {set_code} card {card['id']}: name is empty or N/A"
            )

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] in BASE_EXPECTED_COUNTS
    ])
    def test_number_format(self, load_standard, lang, set_code):
        """Card numbers must contain a dash (e.g. OP11-001, ST07-001, P-105)."""
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        for card in cards:
            assert "-" in card["number"], (
                f"[{lang}] {set_code}: card number '{card['number']}' has no dash"
            )


class TestTypeClassSemantics:
    """Standard sites: type = rarity code, class = card role."""

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] == "OP11"
    ])
    def test_has_leader_card(self, load_standard, lang, set_code):
        """Set must contain at least one LEADER card."""
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        leaders = [c for c in cards if c["type"] == "L"]
        assert len(leaders) > 0, f"[{lang}] OP11 has no cards with type='L'"

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] == "OP11"
    ])
    def test_rarity_codes(self, load_standard, lang, set_code):
        """Rarity (type field) must start with a known code. Some sites use
        localized forms like 'SP CARD', 'SPカード', 'SP卡'; we check that the
        rarity starts with a known prefix."""
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        valid_prefixes = ("L", "C", "UC", "R", "SR", "SEC", "SP", "P", "TR", "M")
        for card in cards:
            rarity = card["type"]
            assert any(rarity == p or rarity.startswith(p + " ") or
                       (rarity.startswith(p) and len(p) > 1)
                       for p in valid_prefixes), (
                f"[{lang}] Card {card['number']}: rarity '{rarity}' "
                f"does not start with any of {valid_prefixes}"
            )


class TestParallelCards:
    """Parallel art cards: id has _p suffix, number stays clean."""

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] == "OP11"
    ])
    def test_parallel_number_is_clean(self, load_standard, lang, set_code):
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        for card in cards:
            if "_p" in card["id"].lower():
                assert "_p" not in card["number"].lower(), (
                    f"[{lang}] Parallel card {card['id']}: "
                    f"number '{card['number']}' should not contain _p suffix"
                )


class TestCostLabelsStripped:
    """The _text() helper must strip <h3> labels, leaving only the value."""

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] == "OP11"
    ])
    def test_cost_is_numeric(self, load_standard, lang, set_code):
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        for card in cards:
            cost = card["cost"]
            if cost == "N/A":
                continue
            assert cost.isdigit(), (
                f"[{lang}] Card {card['number']}: cost '{cost}' should be numeric"
            )

    @pytest.mark.parametrize("lang,set_code", [
        p for p in STANDARD_FIXTURES if p[1] == "OP11"
    ])
    def test_power_is_numeric(self, load_standard, lang, set_code):
        """Power must be numeric or a sentinel (N/A, -)."""
        soup = load_standard(lang, set_code)
        cards = parse_cards_standard(soup, lang)
        sentinels = {"N/A", "-", ""}
        for card in cards:
            power = card["power"]
            if power in sentinels:
                continue
            assert power.isdigit(), (
                f"[{lang}] Card {card['number']}: power '{power}' should be numeric"
            )
