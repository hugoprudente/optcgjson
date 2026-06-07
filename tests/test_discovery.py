"""Tests for series discovery page parsing."""
from __future__ import annotations

import pytest
from optcg.providers.official_site import parse_discovery_standard, parse_discovery_kr


class TestStandardDiscovery:

    def test_en_discovers_sets(self, load_discovery):
        soup = load_discovery("en_cardlist")
        results = parse_discovery_standard(soup, "en")
        assert len(results) > 40, f"Expected 40+ series, got {len(results)}"

    def test_en_contains_target_sets(self, load_discovery):
        soup = load_discovery("en_cardlist")
        results = parse_discovery_standard(soup, "en")
        codes = {code for code, _ in results}
        for expected in ("OP11", "ST07", "PRB01", "EB02", "OP15"):
            assert expected in codes, f"{expected} not found in discovery"

    def test_en_set_codes_are_alphanumeric(self, load_discovery):
        soup = load_discovery("en_cardlist")
        results = parse_discovery_standard(soup, "en")
        for code, _ in results:
            assert code.replace("-", "").isalnum(), (
                f"Set code '{code}' contains non-alphanumeric chars"
            )

    def test_en_series_ids_are_positive(self, load_discovery):
        soup = load_discovery("en_cardlist")
        results = parse_discovery_standard(soup, "en")
        for code, sid in results:
            assert sid > 0, f"{code}: series ID {sid} should be positive"


class TestKrDiscovery:

    def test_ko_discovers_sets(self, load_discovery):
        soup = load_discovery("ko_cardlist")
        results = parse_discovery_kr(soup)
        assert len(results) > 20, f"Expected 20+ KR series, got {len(results)}"

    def test_ko_contains_target_sets(self, load_discovery):
        soup = load_discovery("ko_cardlist")
        results = parse_discovery_kr(soup)
        codes = {code for code, _ in results}
        for expected in ("OP11", "ST07", "EB02"):
            assert expected in codes, f"{expected} not found in KR discovery"

    def test_ko_maps_prefixes(self, load_discovery):
        """OPK -> OP, STK -> ST, EBK -> EB in set codes."""
        soup = load_discovery("ko_cardlist")
        results = parse_discovery_kr(soup)
        codes = {code for code, _ in results}
        assert not any(c.startswith("OPK") for c in codes), "OPK prefix should be mapped to OP"
        assert not any(c.startswith("STK") for c in codes), "STK prefix should be mapped to ST"
        assert not any(c.startswith("EBK") for c in codes), "EBK prefix should be mapped to EB"

    def test_ko_synthetic_ids_are_deterministic(self, load_discovery):
        """Running discovery twice should produce the same IDs."""
        soup = load_discovery("ko_cardlist")
        results1 = parse_discovery_kr(soup)
        results2 = parse_discovery_kr(soup)
        assert results1 == results2, "KR synthetic IDs are not deterministic"
