"""Tests for the foreign-data merge pipeline."""
from __future__ import annotations

import pytest
from optcg.pipeline.normalize import normalize_card
from optcg.pipeline.merge import merge_foreign_data


def _make_card(number: str, name: str, effect: str = "eff") -> dict:
    return normalize_card({
        "id": number, "number": number, "type": "C", "class": "CHARACTER",
        "name": name, "cost": "3", "attribute": ["Strike"],
        "trigger": "N/A", "power": "4000", "counter": "1000",
        "color": ["Red"], "feature": ["Navy"],
        "block_icon": "3", "effect": effect,
        "card_set": "Test Set", "image_url": f"https://example.com/{number}.png",
    })


class TestMergeForeignData:

    def test_single_foreign_language(self):
        primary = [_make_card("OP11-001", "Koby")]
        foreign = {
            "ja": [_make_card("OP11-001", "コビー", "日本語効果")],
        }
        result = merge_foreign_data(primary, foreign)
        card = result[0]
        assert "Japanese" in card["languages"]
        assert card["foreign_data"] is not None
        assert len(card["foreign_data"]) == 1
        assert card["foreign_data"][0]["language"] == "Japanese"
        assert card["foreign_data"][0]["name"] == "コビー"

    def test_multiple_foreign_languages(self):
        primary = [_make_card("OP11-001", "Koby")]
        foreign = {
            "ja": [_make_card("OP11-001", "コビー")],
            "ko": [_make_card("OP11-001", "코비")],
        }
        result = merge_foreign_data(primary, foreign)
        card = result[0]
        assert len(card["foreign_data"]) == 2
        langs = {fd["language"] for fd in card["foreign_data"]}
        assert "Japanese" in langs
        assert "Korean" in langs

    def test_unmatched_foreign_card_ignored(self):
        primary = [_make_card("OP11-001", "Koby")]
        foreign = {
            "ja": [_make_card("OP11-999", "Unknown")],
        }
        result = merge_foreign_data(primary, foreign)
        card = result[0]
        assert card["foreign_data"] is None

    def test_merge_by_number(self):
        """Merge uses card number for matching, not id."""
        primary = [_make_card("OP11-002", "Ain")]
        foreign = {
            "ja": [_make_card("OP11-002", "アイン")],
        }
        result = merge_foreign_data(primary, foreign)
        assert result[0]["foreign_data"][0]["name"] == "アイン"
