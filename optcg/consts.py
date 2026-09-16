"""Constants for the OPTCG pipeline."""

from __future__ import annotations

VERSION = "1.0.0"

# Sentinel values that the official site uses for "no data".
SENTINEL_VALUES = frozenset({"N/A", "-", ""})

# Language registry -- each language endpoint on the official card-list site.
# The "primary" language is used as the base card data; all others become
# foreignData entries on each card.
#
# site_type values:
#   "standard"  -- uses *.onepiece-cardgame.com/cardlist/?series=<numeric_id>
#                   with <dl class="modalCol"> card markup (EN, JA, FR, TH, TC, NA/EU)
#   "kr"        -- onepiece-cardgame.kr, completely different domain, URL scheme,
#                   set-code prefix (OPK-), and HTML layout.  Needs its own provider.
#   "cn"        -- www.onepiece-cardgame.cn, JS-rendered SPA.  Cannot be scraped
#                   with requests+bs4.
LANGUAGES: dict[str, dict] = {
    "en": {
        "name": "English",
        "subdomain": "asia-en",
        "base_url": "https://asia-en.onepiece-cardgame.com",
        "site_type": "standard",
        "primary": True,
    },
    "ja": {
        "name": "Japanese",
        "subdomain": "www",
        "base_url": "https://www.onepiece-cardgame.com",
        "site_type": "standard",
    },
    "fr": {
        "name": "French",
        "subdomain": "fr",
        "base_url": "https://fr.onepiece-cardgame.com",
        "site_type": "standard",
    },
    "zh-Hant": {
        "name": "Chinese Traditional",
        "subdomain": "asia-tc",
        "base_url": "https://asia-tc.onepiece-cardgame.com",
        "site_type": "standard",
    },
    "th": {
        "name": "Thai",
        "subdomain": "asia-th",
        "base_url": "https://asia-th.onepiece-cardgame.com",
        "site_type": "standard",
    },
    "en-na": {
        "name": "English (NA/EU)",
        "subdomain": "en",
        "base_url": "https://en.onepiece-cardgame.com",
        "site_type": "standard",
    },
    "ko": {
        "name": "Korean",
        "subdomain": "kr",
        "base_url": "https://onepiece-cardgame.kr",
        "site_type": "kr",
    },
    "zh-Hans": {
        "name": "Chinese Simplified",
        "subdomain": "cn",
        "base_url": "https://www.onepiece-cardgame.cn",
        "site_type": "cn",
    },
}

PRIMARY_LANG = next(k for k, v in LANGUAGES.items() if v.get("primary"))

# Set type derived from code prefix.
SET_TYPE_PREFIXES: dict[str, str] = {
    "OP": "booster",
    "ST": "starter",
    "EB": "extra_booster",
    "PRB": "premium_booster",
}

# Fallback type for codes that don't match any prefix (promos, family decks, etc.)
DEFAULT_SET_TYPE = "special"


def set_type_for_code(code: str) -> str:
    """Derive the set type from a set code like 'OP15' or 'ST01'."""
    for prefix, stype in SET_TYPE_PREFIXES.items():
        if code.upper().startswith(prefix):
            return stype
    return DEFAULT_SET_TYPE


def clean_sentinel(value: str | None) -> str | None:
    """Return None if the value is a sentinel, otherwise the value unchanged."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() in SENTINEL_VALUES:
        return None
    return value
