"""File envelope helpers -- every output file uses {meta, data}."""

from __future__ import annotations

import datetime

from optcg.consts import VERSION


def make_envelope(data, *, extra_meta: dict | None = None) -> dict:
    """Wrap *data* in the standard ``{meta, data}`` envelope."""
    meta: dict = {
        "date": datetime.date.today().isoformat(),
        "version": VERSION,
    }
    if extra_meta:
        meta.update(extra_meta)
    return {"meta": meta, "data": data}
