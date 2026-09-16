"""Generate a downstream-friendly ``series_map.yaml`` in ``output/``.

The canonical ``series_map.yaml`` at the repository root uses a per-language
schema (``series: {en: [556116], ja: [...]}``) and only carries codes, names
and series IDs. Downstream consumers like ``punkrecords`` expect a flattened
schema that also includes ``image`` and ``releaseDate``::

    OP16:
      name: "BOOSTER PACK -... - [OP-16]"
      series: [556116]
      image: "/images/sets/op16.png"
      releaseDate: ""

This module assembles that flattened YAML from:

* the assembled set dicts (``name``, ``release_date`` -- community names that
  come from the official site scraper),
* the canonical ``series_map.yaml`` (series IDs for the primary language),
* the ``SET_TYPE_PREFIXES`` convention (per-set image path).

It writes ``output/series_map.yaml`` so downstream projects can pick it up as
a starting point and hand-edit anything that the upstream site does not yet
publish (typically release dates for unreleased sets, or names for sets the
site has not announced yet).
"""
from __future__ import annotations

import html as html_mod
import json
import os
import re
import sys

from optcg.consts import PRIMARY_LANG, SET_TYPE_PREFIXES
from optcg.providers.official_site._helpers import BASE_DIR
from optcg.providers.official_site._yaml_map import load_series_map

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "series_map.yaml")
RAW_SETS_DIR = os.path.join(BASE_DIR, "sets", PRIMARY_LANG)


def _print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def _clean_name(text: str | None) -> str:
    if not text:
        return ""
    return html_mod.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _scraped_name(code: str) -> str:
    """Read the latest community name from the first card's ``card_set`` field
    in the raw scraped ``sets/<PRIMARY_LANG>/<CODE>.json``. This is the source
    of truth even when the build pipeline pinned a placeholder name."""
    path = os.path.join(RAW_SETS_DIR, f"{code}.json")
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""
    cards = (payload.get("data") or {}).get("cards") or []
    if not cards:
        return ""
    return _clean_name(cards[0].get("card_set"))


def _image_path(code: str) -> str:
    """Image path for the downstream site. Empty for non-standard set codes
    (Family Deck Set, Limited Product Card, Promotion card, etc.)."""
    upper = code.upper()
    for prefix in SET_TYPE_PREFIXES:
        if upper.startswith(prefix):
            return f"/images/sets/{code.lower()}.png"
    return ""


def _primary_series_ids(canonical_entry: dict) -> list[int]:
    series = canonical_entry.get("series")
    if isinstance(series, dict):
        ids = series.get(PRIMARY_LANG, [])
    elif isinstance(series, list):
        ids = series
    else:
        ids = []
    return [int(s) for s in ids if isinstance(s, int) or (isinstance(s, str) and s.isdigit())]


def build_series_map_yaml(sets: list[dict]) -> str:
    """Return the YAML text for the downstream series map.

    *sets* are the assembled set dicts (output of the build pipeline). The
    function tolerates an empty list and will then fall back to the canonical
    map only -- useful for a standalone ``series-map`` CLI run.
    """
    canonical_map = load_series_map()
    by_code = {s.get("code"): s for s in sets if s.get("code")}
    all_codes = sorted(set(by_code.keys()) | set(canonical_map.keys()))

    lines: list[str] = []
    for code in all_codes:
        set_dict = by_code.get(code, {})
        canonical = canonical_map.get(code, {})

        # Resolve the display name through ordered fallbacks. A name that just
        # repeats the code (e.g. ``"OP16"``) is a placeholder; treat it as
        # missing so the next candidate gets a chance.
        candidates = [
            _clean_name(set_dict.get("name")),
            _clean_name(canonical.get("name")),
            _scraped_name(code),
        ]
        name = code
        for candidate in candidates:
            if candidate and candidate != code:
                name = candidate
                break

        series_ids = _primary_series_ids(canonical)
        image = _image_path(code)
        release_date = set_dict.get("release_date") or ""

        ids_str = ", ".join(str(s) for s in series_ids)
        safe_name = name.replace('"', '\\"')

        lines.append(f"{code}:")
        lines.append(f'  name: "{safe_name}"')
        lines.append(f"  series: [{ids_str}]")
        lines.append(f'  image: "{image}"')
        lines.append(f'  releaseDate: "{release_date}"')

    return "\n".join(lines) + "\n"


def assemble_series_map_yaml(sets: list[dict]) -> str:
    """Write the downstream series_map.yaml to ``output/`` and return its path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    text = build_series_map_yaml(sets)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    _print(f"[write] {OUTPUT_FILE}")
    return OUTPUT_FILE
