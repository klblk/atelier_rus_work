#!/usr/bin/env python3
"""Copy generated telop sprite PNGs into PACK00D1scripts/a19_telop_XX/ folders."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from telop_generate_common import (
    A19_TELOPS_DIR,
    DEFAULT_SPRITES_JSON,
    SPRITES_OUT_DIR,
)

PACK00D1SCRIPTS_DIR = A19_TELOPS_DIR.parent


def load_sprites(sprites_json: Path) -> list[dict]:
    data = json.loads(sprites_json.read_text(encoding="utf-8"))
    sprites = data.get("sprites", [])
    if not isinstance(sprites, list):
        raise SystemExit(f"{sprites_json}: expected sprites array")
    return [s for s in sprites if str(s.get("text", "")).strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sprites-json",
        type=Path,
        default=DEFAULT_SPRITES_JSON,
        help="sprites manifest (default: a19_telops/sprites.json)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SPRITES_OUT_DIR,
        help="generated PNG directory (default: build/a19_telops/sprites)",
    )
    parser.add_argument(
        "--g1t",
        action="append",
        default=[],
        help="only copy sprites for this atlas (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print actions without copying",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="skip destination files that already exist",
    )
    args = parser.parse_args()

    sprites_json = args.sprites_json.resolve()
    source_dir = args.source.resolve()
    g1t_filter = set(args.g1t)

    if not sprites_json.is_file():
        raise SystemExit(f"sprites json not found: {sprites_json}")
    if not source_dir.is_dir():
        raise SystemExit(f"source dir not found: {source_dir}")

    copied = 0
    skipped = 0
    missing = 0

    for sprite in load_sprites(sprites_json):
        g1t = sprite["g1t"]
        if g1t_filter and g1t not in g1t_filter:
            continue

        sprite_id = sprite["id"]
        src = source_dir / f"{sprite_id}.png"
        dest_dir = PACK00D1SCRIPTS_DIR / g1t
        dest = dest_dir / f"{sprite_id}.png"

        if not src.is_file():
            print(f"missing: {src}")
            missing += 1
            continue

        if args.no_overwrite and dest.is_file():
            print(f"skip (exists): {dest}")
            skipped += 1
            continue

        print(f"{'would copy' if args.dry_run else 'copy'}: {src} -> {dest}")
        if not args.dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        copied += 1

    print(
        f"\nSummary: copied={copied}, skipped={skipped}, missing={missing}"
        + (" (dry-run)" if args.dry_run else "")
    )
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
