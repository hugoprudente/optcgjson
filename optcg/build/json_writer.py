"""Write output JSON files with the standard ``{meta, data}`` envelope."""

from __future__ import annotations

import json
import os
import sys

from optcg.models.files import make_envelope


def _print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def write_json(data, path: str, *, extra_meta: dict | None = None) -> None:
    """Write *data* wrapped in an envelope to *path*."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    envelope = make_envelope(data, extra_meta=extra_meta)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
    _print(f"[write] {path}")


def write_json_streaming(data_dict: dict, path: str, *, extra_meta: dict | None = None) -> None:
    """Write a large dict-based data payload to *path* by streaming one
    top-level key at a time, to limit peak memory when building AllSets.

    The output is valid JSON wrapped in the standard envelope.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    envelope = make_envelope(None, extra_meta=extra_meta)
    meta_json = json.dumps(envelope["meta"], ensure_ascii=False, indent=2)

    with open(path, "w", encoding="utf-8") as f:
        f.write('{\n  "meta": ')
        f.write(meta_json)
        f.write(',\n  "data": {\n')

        keys = sorted(data_dict.keys())
        for i, key in enumerate(keys):
            value_json = json.dumps(data_dict[key], ensure_ascii=False, indent=2)
            # Indent the value block by 4 spaces.
            indented = "\n".join(
                ("    " + line if line.strip() else line) for line in value_json.split("\n")
            )
            f.write(f'    {json.dumps(key)}: {indented.lstrip()}')
            if i < len(keys) - 1:
                f.write(",")
            f.write("\n")

        f.write("  }\n}\n")

    _print(f"[write] {path} (streaming)")
