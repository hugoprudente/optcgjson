"""Tests for the normalization pipeline."""
from __future__ import annotations

import pytest
from optcg.pipeline.normalize import normalize_card


class TestNormalizeCard:

    def test_basic_normalization(self):
        raw = {
            "id": "OP11-001",
            "number": "OP11-001",
            "type": "L",
            "class": "LEADER",
            "name": "Koby",
            "cost": "4",
            "attribute": ["Strike"],
            "trigger": "N/A",
            "power": "5000",
            "counter": "-",
            "color": ["Red", "Black"],
            "feature": ["Navy", "SWORD"],
            "block_icon": "3",
            "effect": "Some effect text.",
            "card_set": "-A Fist of Divine Speed- [OP-11]",
            "image_url": "https://example.com/OP11-001.png",
        }
        result = normalize_card(raw)
        assert result["id"] == "OP11-001"
        assert result["number"] == "OP11-001"
        assert result["name"] == "Koby"
        assert result["rarity"] == "L"
        assert result["card_class"] == "LEADER"
        # Leaders: the scraped value belongs to ``life``, not ``cost``.
        assert result["cost"] is None
        assert result["life"] == "4"
        assert result["power"] == "5000"
        assert result["counter"] is None  # "-" is a sentinel
        assert result["trigger"] is None  # "N/A" is a sentinel
        assert result["color"] == ["Red", "Black"]
        assert result["feature"] == ["Navy", "SWORD"]
        assert result["attribute"] == ["Strike"]
        assert result["is_parallel"] is False

    def test_non_leader_keeps_cost(self):
        raw = {
            "id": "OP01-004", "number": "OP01-004",
            "type": "C", "class": "CHARACTER",
            "name": "Usopp", "cost": "2",
            "attribute": ["Ranged"], "trigger": "N/A",
            "power": "2000", "counter": "1000",
            "color": ["Red"], "feature": ["Straw Hat Crew"],
            "block_icon": "1", "effect": "",
            "card_set": "", "image_url": "",
        }
        result = normalize_card(raw)
        assert result["card_class"] == "CHARACTER"
        assert result["cost"] == "2"
        assert result["life"] is None

    def test_korean_leader_split(self):
        # The Korean scraper emits the localised class "리더" and assigns the
        # life value to the raw ``cost`` field; normalize must still detect it.
        raw = {
            "id": "OP01-001", "number": "OP01-001",
            "type": "L", "class": "리더",
            "name": "몽키.D.루피", "cost": "5",
            "attribute": [], "trigger": "N/A",
            "power": "5000", "counter": "-",
            "color": [], "feature": [],
            "block_icon": "1", "effect": "",
            "card_set": "", "image_url": "",
        }
        result = normalize_card(raw)
        assert result["card_class"] == "리더"
        assert result["cost"] is None
        assert result["life"] == "5"

    def test_sentinel_cleaning(self):
        raw = {
            "id": "X", "number": "X", "type": "", "class": "",
            "name": "N/A", "cost": "N/A", "attribute": [],
            "trigger": "-", "power": "", "counter": "N/A",
            "color": [], "feature": [], "block_icon": "N/A",
            "effect": "N/A", "card_set": "", "image_url": "",
        }
        result = normalize_card(raw)
        # name uses strip() not _clean(), so "N/A" stays as literal string
        assert result["name"] == "N/A"
        assert result["cost"] is None
        assert result["life"] is None
        assert result["trigger"] is None
        assert result["power"] is None
        assert result["counter"] is None

    def test_parallel_detection(self):
        raw = {
            "id": "OP11-001_p1", "number": "OP11-001",
            "type": "L", "class": "LEADER", "name": "Koby",
            "cost": "4", "attribute": [], "trigger": "N/A",
            "power": "5000", "counter": "-", "color": [],
            "feature": [], "block_icon": "3", "effect": "",
            "card_set": "", "image_url": "",
        }
        result = normalize_card(raw)
        assert result["is_parallel"] is True

    def test_parallel_detection_uppercase(self):
        raw = {
            "id": "OP11-001_P1", "number": "OP11-001_P1",
            "type": "L", "class": "LEADER", "name": "Koby",
            "cost": "4", "attribute": [], "trigger": "N/A",
            "power": "5000", "counter": "-", "color": [],
            "feature": [], "block_icon": "3", "effect": "",
            "card_set": "", "image_url": "",
        }
        result = normalize_card(raw)
        assert result["is_parallel"] is True

    def test_list_from_string(self):
        raw = {
            "id": "X", "number": "X", "type": "", "class": "",
            "name": "Test", "cost": "1", "attribute": "Strike/Ranged",
            "trigger": "", "power": "1000", "counter": "1000",
            "color": "Red/Blue", "feature": "Navy/SWORD",
            "block_icon": "", "effect": "", "card_set": "", "image_url": "",
        }
        result = normalize_card(raw)
        assert result["attribute"] == ["Strike", "Ranged"]
        assert result["color"] == ["Red", "Blue"]
        assert result["feature"] == ["Navy", "SWORD"]
