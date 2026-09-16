"""Pipeline orchestrator -- runs normalisation, validation, and merge."""

from __future__ import annotations

import sys

from optcg.consts import LANGUAGES, PRIMARY_LANG, set_type_for_code
from optcg.data.context import PipelineContext
from optcg.models.cards import card_to_dict
from optcg.models.sets import new_set, set_to_dict, set_summary
from optcg.pipeline.normalize import normalize_card
from optcg.pipeline.validate import validate_card, validate_set
from optcg.pipeline.merge import merge_foreign_data


def _print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def build_set(code: str, ctx: PipelineContext) -> dict | None:
    """Build a fully normalised set dict (internal schema) for *code*."""
    primary_raw = ctx.raw_cards(code, PRIMARY_LANG)
    if not primary_raw:
        _print(f"[build] No primary-language data for {code}, skipping.")
        return None

    primary_cards = [normalize_card(c) for c in primary_raw]

    errors: list[str] = []
    for card in primary_cards:
        errors.extend(validate_card(card))
    if errors:
        for e in errors:
            _print(f"[validate] {e}")

    # Normalise foreign-language cards.
    foreign: dict[str, list[dict]] = {}
    for lang in ctx.available_langs(code):
        if lang == PRIMARY_LANG:
            continue
        raw_foreign = ctx.raw_cards(code, lang)
        if raw_foreign:
            foreign[lang] = [normalize_card(c) for c in raw_foreign]

    merge_foreign_data(primary_cards, foreign)

    # Count non-parallel cards for base_set_size.
    base_count = sum(1 for c in primary_cards if not c.get("is_parallel"))
    total_count = len(primary_cards)

    # Determine available languages and foreign names.
    available_langs = ctx.available_langs(code)
    lang_names = [LANGUAGES[l]["name"] for l in available_langs if l in LANGUAGES]
    foreign_names: dict[str, str] = {}
    for lang in available_langs:
        if lang == PRIMARY_LANG:
            continue
        fname = ctx.set_name_for_lang(code, lang)
        if fname:
            foreign_names[LANGUAGES[lang]["name"]] = fname

    # Set name precedence:
    #   1. ``series_map.yaml`` when hand-curated (any value other than the
    #      bare code, which is a discovery-time placeholder),
    #   2. the scraped ``card_set`` field from the live site,
    #   3. the code itself.
    # This preserves curated overrides like
    # ``BOOSTER PACK -Adventure on KAMI's Island- [OP-15]`` while still
    # picking up real names for sets that only have a placeholder entry
    # (e.g. brand-new ``OP16``).
    map_name = (ctx.series_map.get(code, {}).get("name") or "").strip()
    if map_name == code:
        map_name = ""
    scraped_name = ctx.set_name_for_lang(code, PRIMARY_LANG)
    set_name = map_name or scraped_name or code

    s = new_set(
        code=code,
        name=set_name,
        type=set_type_for_code(code),
        release_date=None,
        base_set_size=base_count,
        total_set_size=total_count,
        languages=lang_names,
        foreign_names=foreign_names if foreign_names else None,
        cards=primary_cards,
    )

    set_errors = validate_set(s)
    if set_errors:
        for e in set_errors:
            _print(f"[validate] {e}")

    return s


def build_all(ctx: PipelineContext) -> list[dict]:
    """Build all sets that have primary-language data."""
    sets: list[dict] = []
    for code in ctx.set_codes:
        s = build_set(code, ctx)
        if s:
            sets.append(s)
    _print(f"[build] Built {len(sets)} sets.")
    return sets
