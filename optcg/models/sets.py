"""Set dict schema and serialisation helpers."""

from __future__ import annotations


SET_FIELDS = [
    "code",
    "name",
    "type",
    "release_date",
    "base_set_size",
    "total_set_size",
    "languages",
    "foreign_names",
    "cards",
]


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def new_set(**kwargs) -> dict:
    """Create a set dict with all expected keys."""
    s: dict = {}
    for field in SET_FIELDS:
        s[field] = kwargs.get(field)
    return s


def set_to_dict(s: dict) -> dict:
    """Serialise a set dict to camelCase JSON-ready dict."""
    out: dict = {}
    for field in SET_FIELDS:
        value = s.get(field)
        key = _to_camel(field)
        out[key] = value
    return out


def set_summary(s: dict) -> dict:
    """Return a lightweight summary of a set (for SetList.json)."""
    return {
        "code": s.get("code"),
        "name": s.get("name"),
        "type": s.get("type"),
        "releaseDate": s.get("release_date"),
        "baseSetSize": s.get("base_set_size"),
        "totalSetSize": s.get("total_set_size"),
        "languages": s.get("languages"),
    }
