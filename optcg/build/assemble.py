"""Assembly layer -- convert internal set dicts into output files."""

from __future__ import annotations

import os

from optcg.models.cards import card_to_dict
from optcg.models.sets import set_to_dict, set_summary
from optcg.build.json_writer import write_json, write_json_streaming
from optcg.providers.official_site import BASE_DIR

OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def _serialise_set(s: dict) -> dict:
    """Serialise a set and its cards to camelCase dicts."""
    cards = s.get("cards") or []
    out = set_to_dict(s)
    out["cards"] = [card_to_dict(c) for c in cards]
    return out


def assemble_set(s: dict) -> None:
    """Write a single per-set output file: ``output/{CODE}.json``."""
    code = s["code"]
    payload = _serialise_set(s)
    path = os.path.join(OUTPUT_DIR, f"{code}.json")
    write_json(payload, path)


def assemble_set_list(sets: list[dict]) -> None:
    """Write ``output/SetList.json``."""
    summaries = [set_summary(s) for s in sets]
    path = os.path.join(OUTPUT_DIR, "SetList.json")
    write_json(summaries, path)


def assemble_all_sets(sets: list[dict]) -> None:
    """Write ``output/AllSets.json`` using streaming to limit memory."""
    all_data: dict[str, dict] = {}
    for s in sets:
        code = s["code"]
        all_data[code] = _serialise_set(s)
    path = os.path.join(OUTPUT_DIR, "AllSets.json")
    write_json_streaming(all_data, path)


def assemble_all(sets: list[dict]) -> None:
    """Run the full assembly: per-set files, SetList, AllSets."""
    for s in sets:
        assemble_set(s)
    assemble_set_list(sets)
    assemble_all_sets(sets)
