#!/usr/bin/env python3
"""Build letter → carrier map for phys_glyph."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from kanji_carriers import KANJI_100
from phys_glyph_common import (
    BUILD_CARRIER_SCRIPT,
    BUILD_VIRTUAL_SCRIPT,
    DEFAULT_EXE_IN,
    LETTER_CARRIER_MAP_BACKUP_JSON,
    LETTER_CARRIER_MAP_JSON,
    PHYS_BLOCK_MAP_JSON,
    PHYS_GLYPH_DIR,
    SCAN_SCRIPT,
    VIRTUAL_JSON,
)


def run_script(script: Path, extra_args: list[str]) -> None:
    print(f"running {script.name} {' '.join(extra_args)}...")
    subprocess.run(
        [sys.executable, str(script), *extra_args],
        check=True,
        cwd=PHYS_GLYPH_DIR,
    )


def ensure_prerequisites(exe: Path, *, force: bool) -> None:
    scan_args = ["--exe", str(exe)]
    if force:
        scan_args.append("--force")
    if force or not PHYS_BLOCK_MAP_JSON.is_file():
        run_script(SCAN_SCRIPT, scan_args)

    virtual_args: list[str] = []
    if force:
        virtual_args.append("--force")
    if force or not VIRTUAL_JSON.is_file():
        run_script(BUILD_VIRTUAL_SCRIPT, virtual_args)


def load_virtual_keys(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.keys())


def build_map(keys: list[str], fill_kanji: bool) -> dict[str, str]:
    if not fill_kanji:
        return {k: "" for k in keys}

    if len(keys) > len(KANJI_100):
        print(
            f"warning: {len(keys)} keys exceed KANJI_100 length {len(KANJI_100)}; truncating",
            file=sys.stderr,
        )
    return {keys[i]: KANJI_100[i] for i in range(min(len(keys), len(KANJI_100)))}


def build_letter_carrier_map(
    *,
    exe: Path = DEFAULT_EXE_IN,
    out_json: Path = LETTER_CARRIER_MAP_JSON,
    fill_kanji: bool = False,
    force: bool = False,
) -> None:
    ensure_prerequisites(exe.resolve(), force=force)

    keys = load_virtual_keys(VIRTUAL_JSON)
    carrier_map = build_map(keys, fill_kanji)

    backup_path: Path | None = None
    if out_json.is_file():
        out_json.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_json, LETTER_CARRIER_MAP_BACKUP_JSON)
        backup_path = LETTER_CARRIER_MAP_BACKUP_JSON

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(carrier_map, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    mode = "fill-kanji" if fill_kanji else "empty"
    print(f"keys: {len(keys)}")
    print(f"mode: {mode}")
    if backup_path is not None:
        print(f"backup: {backup_path}")
    print(f"wrote {out_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE_IN)
    parser.add_argument("--out", type=Path, default=LETTER_CARRIER_MAP_JSON)
    parser.add_argument(
        "--fill-kanji",
        action="store_true",
        help="fill values from KANJI_100 by virtual_phys_blocks key order",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild prerequisite JSON files",
    )
    args = parser.parse_args()
    build_letter_carrier_map(
        exe=args.exe.resolve(),
        out_json=args.out.resolve(),
        fill_kanji=args.fill_kanji,
        force=args.force,
    )


if __name__ == "__main__":
    main()
