"""YAML series-map load/write helpers (no pyyaml dependency)."""
from __future__ import annotations

import html as html_mod
import json
import os
import re

from optcg.consts import PRIMARY_LANG
from optcg.providers.official_site._helpers import BASE_DIR, SERIES_MAP_FILE, _print


def load_series_map() -> dict[str, dict]:
    """Load ``series_map.yaml`` supporting both flat and per-language formats."""
    if not os.path.isfile(SERIES_MAP_FILE):
        return {}

    sets: dict[str, dict] = {}
    current: str | None = None
    in_series_block = False

    with open(SERIES_MAP_FILE, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                in_series_block = False if not line.strip() else in_series_block
                continue

            if not line.startswith(" ") and line.endswith(":"):
                key = line[:-1].strip()
                current = key
                sets[current] = {"name": "", "series": {}}
                in_series_block = False
                continue

            if current is None:
                continue

            stripped = line.strip()

            if stripped.startswith("name:"):
                name_val = stripped[len("name:"):].strip()
                if name_val.startswith(("'", '"')) and name_val.endswith(("'", '"')):
                    name_val = name_val[1:-1]
                sets[current]["name"] = name_val
                in_series_block = False
                continue

            if stripped.startswith("series:") and "[" in stripped:
                series_val = stripped[len("series:"):].strip()
                nums = _parse_int_list(series_val)
                sets[current]["series"] = {PRIMARY_LANG: nums}
                in_series_block = False
                continue

            if stripped == "series:":
                in_series_block = True
                continue

            if in_series_block and ":" in stripped:
                lang_key, rest = stripped.split(":", 1)
                lang_key = lang_key.strip()
                rest = rest.strip()
                if rest.startswith("["):
                    nums = _parse_int_list(rest)
                    sets[current].setdefault("series", {})[lang_key] = nums
                continue

    return sets


def _parse_int_list(text: str) -> list[int]:
    """Parse ``[1, 2, 3]`` into a list of ints."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [int(c.strip()) for c in inner.split(",") if c.strip().isdigit()]
    return []


def write_series_map(series_map: dict[str, dict]) -> None:
    """Write the in-memory series_map back to ``series_map.yaml``."""
    with open(SERIES_MAP_FILE, "w", encoding="utf-8") as f:
        for code in sorted(series_map.keys()):
            info = series_map[code]
            name = info.get("name", "") or ""
            name = html_mod.unescape(re.sub(r"<[^>]+>", "", name)).strip()
            series = info.get("series", {})
            if not isinstance(series, dict):
                series = {PRIMARY_LANG: series} if isinstance(series, list) else {}

            f.write(f"{code}:\n")
            safe = name.replace('"', '\\"')
            f.write(f'  name: "{safe}"\n')
            f.write("  series:\n")
            for lang in sorted(series.keys()):
                ids = series[lang]
                ids_str = ", ".join(str(s) for s in ids)
                f.write(f"    {lang}: [{ids_str}]\n")


def build_series_to_set_code(series_map: dict[str, dict], lang: str) -> dict[int, str]:
    """Invert the YAML map to ``series_id -> set_code`` for a given language."""
    mapping: dict[int, str] = {}
    for set_code, info in series_map.items():
        series = info.get("series", {})
        if not isinstance(series, dict):
            continue
        for sid in series.get(lang, []):
            if isinstance(sid, int):
                mapping[sid] = set_code
    return mapping


def series_ids_for_lang(series_map: dict[str, dict], lang: str) -> list[int]:
    """Collect all series IDs for a given language from the map."""
    ids: set[int] = set()
    for info in series_map.values():
        series = info.get("series", {})
        if not isinstance(series, dict):
            continue
        for sid in series.get(lang, []):
            if isinstance(sid, int):
                ids.add(sid)
    return sorted(ids)
