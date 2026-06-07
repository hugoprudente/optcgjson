"""Pipeline context -- holds all data needed for a build run."""

from __future__ import annotations

from optcg.consts import LANGUAGES, PRIMARY_LANG
from optcg.data.cache import load_all_raw_sets, available_set_codes
from optcg.providers.official_site import load_series_map


class PipelineContext:
    """Collects raw sets, series map, and language metadata for a build."""

    def __init__(self) -> None:
        self.series_map = load_series_map()
        # {set_code: {lang: raw_dict}}
        self.raw_sets = load_all_raw_sets()

    @property
    def set_codes(self) -> list[str]:
        """All set codes with at least primary language data."""
        return sorted(
            code for code, langs in self.raw_sets.items() if PRIMARY_LANG in langs
        )

    def raw_cards(self, code: str, lang: str) -> list[dict]:
        """Return the raw card list for *code* in *lang*, or []."""
        raw = self.raw_sets.get(code, {}).get(lang)
        if raw is None:
            return []
        return (raw.get("data") or {}).get("cards") or []

    def available_langs(self, code: str) -> list[str]:
        """Languages that have raw data for this set."""
        return sorted(self.raw_sets.get(code, {}).keys())

    def set_name_for_lang(self, code: str, lang: str) -> str | None:
        """The set name as scraped for a specific language (from card_set field)."""
        cards = self.raw_cards(code, lang)
        if not cards:
            return None
        return (cards[0].get("card_set") or "").strip() or None
