#!/usr/bin/env python3
"""Build virtual phys-block params for Cyrillic glyphs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from phys_glyph_common import ATLAS_TABLE, VIRTUAL_JSON

UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
EXTRA = "«»≥"
TARGET_LETTERS = UPPER + LOWER + EXTRA

UPPER_M0_EXCEPTIONS = frozenset("ЁЙ")
GUILLEMETS = frozenset("«»")
DEFAULT_TAIL = "0xFFFFFFFF"


def load_atlas_rects(path: Path) -> dict[str, dict[str, int]]:
    rects: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            letter = row.get("letter", "").strip()
            if not letter:
                continue
            rects[letter] = {
                "x": int(row["x"]),
                "y": int(row["y"]),
                "w": int(row["w"]),
                "h": int(row["h"]),
            }
    return rects


def m0_for_letter(letter: str) -> int:
    if letter in GUILLEMETS:
        return 8
    if letter in UPPER:
        return 3 if letter in UPPER_M0_EXCEPTIONS else 10
    if letter in LOWER:
        return 9
    if letter == "≥":
        return 10
    raise ValueError(f"unknown letter for m0: {letter!r}")


def build_entry(letter: str, rect: dict[str, int]) -> dict[str, int | str]:
    w = rect["w"]
    return {
        "x": rect["x"],
        "y": rect["y"],
        "w": w,
        "h": rect["h"],
        "m0": m0_for_letter(letter),
        "m1": 0,
        "m2": w,
        "tail": DEFAULT_TAIL,
    }


def build_virtual_phys_blocks(
    *,
    atlas_table: Path = ATLAS_TABLE,
    out_json: Path = VIRTUAL_JSON,
    force: bool = False,
) -> None:
    if not atlas_table.is_file():
        raise SystemExit(f"atlas table not found: {atlas_table}")

    atlas = load_atlas_rects(atlas_table)
    existing: dict[str, dict] = {}
    if out_json.is_file() and not force:
        existing = json.loads(out_json.read_text(encoding="utf-8"))

    added = 0
    skipped = 0
    warnings = 0

    for letter in TARGET_LETTERS:
        if letter in existing and not force:
            skipped += 1
            continue
        rect = atlas.get(letter)
        if rect is None:
            print(f"warning: {letter!r} not found in atlas table", file=sys.stderr)
            warnings += 1
            continue
        existing[letter] = build_entry(letter, rect)
        added += 1

    for entry in existing.values():
        entry.setdefault("tail", DEFAULT_TAIL)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"target letters: {len(TARGET_LETTERS)}")
    print(f"added: {added}")
    print(f"skipped (already present): {skipped}")
    print(f"warnings: {warnings}")
    print(f"total in json: {len(existing)}")
    print(f"wrote {out_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-table", type=Path, default=ATLAS_TABLE)
    parser.add_argument("--out", type=Path, default=VIRTUAL_JSON)
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild all target letters from atlas table",
    )
    args = parser.parse_args()
    build_virtual_phys_blocks(
        atlas_table=args.atlas_table.resolve(),
        out_json=args.out.resolve(),
        force=args.force,
    )


if __name__ == "__main__":
    main()
