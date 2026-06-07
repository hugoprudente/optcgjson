"""Shared fixtures for the optcg test suite."""
from __future__ import annotations

import os

import pytest
from bs4 import BeautifulSoup

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
STANDARD_DIR = os.path.join(FIXTURES_DIR, "standard")
KR_DIR = os.path.join(FIXTURES_DIR, "kr")
DISCOVERY_DIR = os.path.join(FIXTURES_DIR, "discovery")


def _load_soup(path: str) -> BeautifulSoup:
    with open(path, "rb") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def load_standard():
    """Return a loader ``(lang, set_code) -> BeautifulSoup`` for standard fixtures."""
    def _load(lang: str, set_code: str) -> BeautifulSoup:
        path = os.path.join(STANDARD_DIR, f"{lang}_{set_code}.html")
        if not os.path.isfile(path):
            pytest.skip(f"Fixture {lang}_{set_code}.html not available")
        return _load_soup(path)
    return _load


@pytest.fixture
def load_kr_pages():
    """Return a loader ``(set_code) -> list[BeautifulSoup]`` for Korean page fixtures."""
    def _load(set_code: str) -> list[BeautifulSoup]:
        pages = []
        for page in range(200):
            path = os.path.join(KR_DIR, f"ko_{set_code}_page{page}.html")
            if not os.path.isfile(path):
                break
            pages.append(_load_soup(path))
        if not pages:
            pytest.skip(f"No KR fixtures for {set_code}")
        return pages
    return _load


@pytest.fixture
def load_discovery():
    """Return a loader ``(name) -> BeautifulSoup`` for discovery page fixtures."""
    def _load(name: str) -> BeautifulSoup:
        path = os.path.join(DISCOVERY_DIR, f"{name}.html")
        if not os.path.isfile(path):
            pytest.skip(f"Discovery fixture {name}.html not available")
        return _load_soup(path)
    return _load


def kr_items_from_pages(pages: list[BeautifulSoup]) -> list:
    """Extract all ``<button class="item">`` elements across KR pages."""
    items = []
    for soup in pages:
        card_list = soup.find("div", class_="card_sch_list")
        if card_list:
            items.extend(card_list.find_all("button", class_="item"))
    return items


# Available standard fixtures (lang, set) pairs
STANDARD_FIXTURES: list[tuple[str, str]] = []
if os.path.isdir(STANDARD_DIR):
    for fname in sorted(os.listdir(STANDARD_DIR)):
        if fname.endswith(".html"):
            stem = fname[:-5]
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                STANDARD_FIXTURES.append((parts[0], parts[1]))
