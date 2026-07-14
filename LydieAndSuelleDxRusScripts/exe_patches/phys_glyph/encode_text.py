#!/usr/bin/env python3
"""Encode text using letter_carrier_map_resolved.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from phys_glyph_common import LETTER_CARRIER_MAP_RESOLVED_JSON

_CONTROL_CODE_RE = re.compile(r"^\^[0-9A-Fa-f]{2}$")


def load_encode_map(resolved_path: Path) -> dict[str, str]:
    data = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {resolved_path}")
    return {str(k): str(v) for k, v in data.items()}


def encode_text(text: str, letter_carrier: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "^" and i + 2 < len(text):
            code = text[i : i + 3]
            if _CONTROL_CODE_RE.match(code):
                out.append(code)
                i += 3
                continue
        ch = text[i]
        if ch in letter_carrier:
            out.append(letter_carrier[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", help="Text to encode (stdout)")
    parser.add_argument("--file", type=Path, help="Read text from file")
    parser.add_argument(
        "--resolved",
        type=Path,
        default=LETTER_CARRIER_MAP_RESOLVED_JSON,
        help="letter_carrier_map_resolved.json path",
    )
    args = parser.parse_args()

    if args.file is not None:
        text = args.file.read_text(encoding="utf-8")
    elif args.text is not None:
        text = args.text
    else:
        parser.error("provide text argument or --file")

    if not args.resolved.is_file():
        raise SystemExit(f"resolved map not found: {args.resolved}")

    letter_carrier = load_encode_map(args.resolved)
    sys.stdout.write(encode_text(text, letter_carrier))


if __name__ == "__main__":
    main()
