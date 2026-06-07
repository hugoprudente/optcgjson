"""
CLI entry-point.

Usage::

    python -m optcg scrape
    python -m optcg scrape --lang ja fr
    python -m optcg scrape --lang all
    python -m optcg scrape --set OP15 --lang ja fr
    python -m optcg scrape --refresh-list --lang all
    python -m optcg build
    python -m optcg all --lang all
    python -m optcg list-sets
"""

from __future__ import annotations

import argparse
import sys

from optcg.consts import LANGUAGES, PRIMARY_LANG


def _print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def _scrapable_langs() -> list[str]:
    """Return language codes whose site_type supports scraping."""
    return [k for k, v in LANGUAGES.items() if v.get("site_type") != "cn"]


def _resolve_langs(raw: list[str] | None) -> list[str]:
    """Resolve a ``--lang`` argument into a list of language codes."""
    if raw is None or not raw:
        return [PRIMARY_LANG]
    if raw == ["all"]:
        return _scrapable_langs()
    for lang in raw:
        if lang not in LANGUAGES:
            _print(f"Unknown language code: {lang}")
            _print(f"Available: {', '.join(LANGUAGES.keys())}")
            sys.exit(1)
    return raw


# -- Subcommand handlers ----------------------------------------------------

def cmd_scrape(args: argparse.Namespace) -> None:
    from optcg.providers.official_site import (
        load_series_map,
        refresh_series_map,
        scrape_sets,
    )

    langs = _resolve_langs(args.lang)

    if args.refresh_list:
        refresh_series_map(langs)
        return

    series_map = load_series_map()
    if not series_map:
        _print("series_map.yaml is empty. Run with --refresh-list first.")
        sys.exit(1)

    set_codes = args.set or None
    for lang in langs:
        scrape_sets(series_map, lang=lang, set_codes=set_codes)


def cmd_build(args: argparse.Namespace) -> None:
    from optcg.data.context import PipelineContext
    from optcg.pipeline.core import build_all
    from optcg.build.assemble import assemble_all

    ctx = PipelineContext()
    sets = build_all(ctx)
    assemble_all(sets)
    _print(f"Build complete. {len(sets)} sets written to output/.")


def cmd_all(args: argparse.Namespace) -> None:
    from optcg.providers.official_site import load_series_map, scrape_sets
    from optcg.data.context import PipelineContext
    from optcg.pipeline.core import build_all
    from optcg.build.assemble import assemble_all

    langs = _resolve_langs(args.lang)
    series_map = load_series_map()
    if not series_map:
        _print("series_map.yaml is empty. Run 'scrape --refresh-list' first.")
        sys.exit(1)

    set_codes = args.set or None
    for lang in langs:
        scrape_sets(series_map, lang=lang, set_codes=set_codes)

    ctx = PipelineContext()
    sets = build_all(ctx)
    assemble_all(sets)
    _print(f"Full pipeline complete. {len(sets)} sets written to output/.")


def cmd_list_sets(args: argparse.Namespace) -> None:
    from optcg.providers.official_site import load_series_map
    series_map = load_series_map()
    if not series_map:
        _print("series_map.yaml is empty.")
        return
    for code in sorted(series_map.keys()):
        info = series_map[code]
        name = info.get("name", "")
        series = info.get("series", {})
        langs = ", ".join(sorted(series.keys())) if isinstance(series, dict) else "?"
        _print(f"  {code:8s} [{langs}]  {name}")


def cmd_refresh_list(args: argparse.Namespace) -> None:
    from optcg.providers.official_site import refresh_series_map
    langs = _resolve_langs(args.lang)
    refresh_series_map(langs)


# -- Argument parser ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="optcg",
        description="OPTCG card data pipeline",
    )
    sub = parser.add_subparsers(dest="command")

    # scrape
    p_scrape = sub.add_parser("scrape", help="Scrape raw card data from the official site")
    p_scrape.add_argument("--lang", nargs="*", help="Language codes (or 'all')")
    p_scrape.add_argument("--set", nargs="*", help="Set codes to scrape (default: all)")
    p_scrape.add_argument("--refresh-list", action="store_true", help="Discover & update series_map.yaml")

    # build
    sub.add_parser("build", help="Build output from raw cache")

    # all
    p_all = sub.add_parser("all", help="Scrape + build in one step")
    p_all.add_argument("--lang", nargs="*", help="Language codes (or 'all')")
    p_all.add_argument("--set", nargs="*", help="Set codes to process (default: all)")

    # list-sets
    sub.add_parser("list-sets", help="List all sets in series_map.yaml")

    # refresh-list
    p_refresh = sub.add_parser("refresh-list", help="Discover series IDs and update series_map.yaml")
    p_refresh.add_argument("--lang", nargs="*", help="Language codes (or 'all')")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "scrape": cmd_scrape,
        "build": cmd_build,
        "all": cmd_all,
        "list-sets": cmd_list_sets,
        "refresh-list": cmd_refresh_list,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
