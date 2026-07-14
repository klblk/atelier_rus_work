#!/usr/bin/env python3
"""Extract PACK00D1, PACK01, and PACK02 from game Data via gust_pak."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PACKUTILS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACKUTILS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    DEFAULT_GAME_DATA_DIR,
    GUST_PAK,
    PACKS_TO_EXTRACT,
    PACK_EXTRACTS_DIR,
    extract_dir_for,
)


def unpack_pak(
    pak_path: Path,
    extracts_root: Path,
    gust_pak: Path,
    *,
    force: bool,
) -> str:
    out_dir = extract_dir_for(pak_path.name, extracts_root)
    if out_dir.exists():
        if not force:
            print(f"Skip extract (exists): {out_dir}")
            return "skipped"
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    dest_pak = out_dir / pak_path.name
    print(f"Copy {pak_path.name} -> {out_dir}")
    shutil.copy2(pak_path, dest_pak)
    print(f"Extract {dest_pak.name} in {out_dir}")
    subprocess.run([str(gust_pak), dest_pak.name], cwd=out_dir, check=True)
    return "extracted"


def extract_packs(
    *,
    data_dir: Path,
    extracts_root: Path,
    gust_pak: Path,
    packs: tuple[str, ...],
    force: bool = False,
) -> dict[str, int]:
    counts = {"extracted": 0, "skipped": 0, "failed": 0}
    extracts_root.mkdir(parents=True, exist_ok=True)

    for name in packs:
        pak_path = data_dir / name
        if not pak_path.is_file():
            print(f"Missing PAK: {pak_path}")
            counts["failed"] += 1
            continue
        try:
            action = unpack_pak(pak_path, extracts_root, gust_pak, force=force)
            counts[action] += 1
        except subprocess.CalledProcessError:
            print(f"Extract failed: {name}")
            counts["failed"] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_GAME_DATA_DIR,
        help="Game Data directory with PACK*.PAK",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PACK_EXTRACTS_DIR,
        help="Root for extracted PAK trees",
    )
    parser.add_argument(
        "--gust-pak",
        type=Path,
        default=GUST_PAK,
        help="Path to gust_pak binary",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if directory exists",
    )
    parser.add_argument(
        "--pack",
        action="append",
        dest="packs",
        metavar="NAME",
        help="Extract only this PAK (repeatable); default: all three",
    )
    args = parser.parse_args()

    if not args.gust_pak.is_file():
        raise SystemExit(f"gust_pak not found: {args.gust_pak}")
    if not args.data_dir.is_dir():
        raise SystemExit(f"data dir not found: {args.data_dir}")

    packs = tuple(args.packs) if args.packs else PACKS_TO_EXTRACT
    counts = extract_packs(
        data_dir=args.data_dir.resolve(),
        extracts_root=args.out_dir.resolve(),
        gust_pak=args.gust_pak.resolve(),
        packs=packs,
        force=args.force,
    )

    print(
        f"Done: extracted={counts['extracted']}, "
        f"skipped={counts['skipped']}, failed={counts['failed']}"
    )
    if counts["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
