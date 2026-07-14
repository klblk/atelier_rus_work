#!/usr/bin/env python3
"""Repack PACK00D1 / PACK01 / PACK02: extract → work → patch overlay → gust_pak."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PACKUTILS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACKUTILS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PACKUTILS_DIR) not in sys.path:
    sys.path.insert(0, str(PACKUTILS_DIR))

from pak_repack import (  # noqa: E402
    SUPPORTED_PACKS,
    normalize_pack_name,
    pack_layout,
    repack_pack,
)
from rus_scripts_common import BUILD_OUT_DATA_DIR, GUST_PAK, PACK_EXTRACTS_DIR  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pack",
        help=f"PACK name: {', '.join(SUPPORTED_PACKS)}",
    )
    parser.add_argument(
        "--extracts-root",
        type=Path,
        default=PACK_EXTRACTS_DIR,
        help="Root for PACK*_extract trees",
    )
    parser.add_argument(
        "--patch-dir",
        type=Path,
        default=None,
        help="Sparse patch overlay (default: build/PACK*_patch for selected pack)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=BUILD_OUT_DATA_DIR,
        help="Output directory for rebuilt PAK files",
    )
    parser.add_argument(
        "--gust-pak",
        type=Path,
        default=GUST_PAK,
        help="Path to gust_pak binary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log steps without copying or packing",
    )
    args = parser.parse_args()

    pack = normalize_pack_name(args.pack)
    patch_dir = args.patch_dir.resolve() if args.patch_dir is not None else None

    layout, overlay_count, out_pak = repack_pack(
        pack,
        extracts_root=args.extracts_root.resolve(),
        patch_dir=patch_dir,
        out_dir=args.out_dir.resolve(),
        gust_pak=args.gust_pak.resolve(),
        dry_run=args.dry_run,
    )

    print(f"pack: {layout.pack}")
    print(f"work: {layout.work_dir}")
    print(f"patch: {layout.patch_dir}")
    print(f"overlay files: {overlay_count}")
    if out_pak is not None:
        print(f"wrote {out_pak}")
        print(f"size: {out_pak.stat().st_size} bytes")


if __name__ == "__main__":
    main()
