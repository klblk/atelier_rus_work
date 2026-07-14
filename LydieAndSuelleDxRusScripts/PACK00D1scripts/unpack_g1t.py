#!/usr/bin/env python3
"""Unpack vanilla mainfont .g1t into build/g1t_work/ via gust_g1t."""

from __future__ import annotations

import argparse
from pathlib import Path

from font_pack_common import (
    DEFAULT_G1T_WORK,
    VANILLA_G1T,
    unpack_g1t_work,
)


def unpack_g1t(
    g1t_path: Path,
    out_work: Path,
    *,
    force: bool = False,
) -> Path:
    out_work = unpack_g1t_work(g1t_path, out_work, force=force)
    print(f"Unpacked -> {out_work}")
    return out_work


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g1t", type=Path, default=VANILLA_G1T, help="input .g1t")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_G1T_WORK,
        help="output work directory (000.dds + g1t.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="recreate output if it already exists",
    )
    args = parser.parse_args()
    unpack_g1t(args.g1t.resolve(), args.out.resolve(), force=args.force)


if __name__ == "__main__":
    main()
