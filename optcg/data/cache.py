"""Load raw scraped JSON files from ``sets/{lang}/``."""

from __future__ import annotations

import json
import os

from optcg.consts import LANGUAGES, PRIMARY_LANG
from optcg.providers.official_site import BASE_DIR


def _sets_dir(lang: str) -> str:
    return os.path.join(BASE_DIR, "sets", lang)


def load_raw_set(code: str, lang: str) -> dict | None:
    """Load a single raw set JSON for a language, or ``None`` if it doesn't exist."""
    path = os.path.join(_sets_dir(lang), f"{code}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def available_set_codes(lang: str) -> list[str]:
    """List set codes that have raw JSON for a given language."""
    d = _sets_dir(lang)
    if not os.path.isdir(d):
        return []
    return sorted(
        f[:-5] for f in os.listdir(d) if f.endswith(".json")
    )


def available_languages_for_set(code: str) -> list[str]:
    """Return language codes that have raw data for the given set."""
    langs: list[str] = []
    for lang in LANGUAGES:
        if os.path.isfile(os.path.join(_sets_dir(lang), f"{code}.json")):
            langs.append(lang)
    return langs


def load_all_raw_sets() -> dict[str, dict[str, dict]]:
    """Load every available raw set grouped by set code then language.

    Returns ``{set_code: {lang: raw_dict, ...}, ...}``.
    """
    result: dict[str, dict[str, dict]] = {}
    for lang in LANGUAGES:
        for code in available_set_codes(lang):
            data = load_raw_set(code, lang)
            if data:
                result.setdefault(code, {})[lang] = data
    return result
