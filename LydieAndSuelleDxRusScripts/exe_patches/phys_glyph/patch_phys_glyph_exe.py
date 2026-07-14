#!/usr/bin/env python3
"""Patch vanilla exe phys blocks from letter_carrier_map."""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

from kanji_carriers import KANJI_100
from phys_glyph_common import (
    BUILD_CARRIER_SCRIPT,
    DEFAULT_EXE_IN,
    DEFAULT_EXE_OUT,
    LETTER_CARRIER_MAP_JSON,
    LETTER_CARRIER_MAP_RESOLVED_JSON,
    PHYS_BLOCK_MAP_JSON,
    PHYS_GLYPH_DIR,
    VIRTUAL_JSON,
)

RECORD_SIZE = 28
PHYS_OFF_RECT = 4
PHYS_OFF_TAIL = 12
PHYS_OFF_METRICS = 16

KANJI_SET = set(KANJI_100)


def parse_code(hex_str: str) -> int:
    return int(hex_str, 16)


def parse_off(hex_str: str) -> int:
    return int(hex_str, 16)


def run_build_carrier_map(exe: Path, *, force: bool) -> None:
    print("running build_letter_carrier_map.py --fill-kanji...")
    args = [
        sys.executable,
        str(BUILD_CARRIER_SCRIPT),
        "--fill-kanji",
        "--exe",
        str(exe),
    ]
    if force:
        args.append("--force")
    subprocess.run(args, check=True, cwd=PHYS_GLYPH_DIR)


def load_maps(exe: Path, *, force: bool) -> tuple[dict, dict[str, dict], dict[str, dict], list[str]]:
    if force or not LETTER_CARRIER_MAP_JSON.is_file():
        run_build_carrier_map(exe, force=force)
    if not LETTER_CARRIER_MAP_JSON.is_file():
        raise SystemExit(f"carrier map not found after build: {LETTER_CARRIER_MAP_JSON}")
    if not PHYS_BLOCK_MAP_JSON.is_file():
        raise SystemExit(f"phys_block_map.json required: {PHYS_BLOCK_MAP_JSON}")
    if not VIRTUAL_JSON.is_file():
        raise SystemExit(f"virtual_phys_blocks.json required: {VIRTUAL_JSON}")

    carrier = json.loads(LETTER_CARRIER_MAP_JSON.read_text(encoding="utf-8"))
    phys_payload = json.loads(PHYS_BLOCK_MAP_JSON.read_text(encoding="utf-8"))
    virtual = json.loads(VIRTUAL_JSON.read_text(encoding="utf-8"))
    scan_range = phys_payload.get("meta", {}).get("scan_range", ["0xC1FF90", "0xC30000"])
    return carrier, phys_payload["blocks"], virtual, scan_range


def resolve_glyph_entry(
    letter1: str,
    virtual: dict[str, dict],
    phys_blocks: dict[str, dict],
) -> dict:
    if letter1 in virtual:
        return virtual[letter1]
    if letter1 in phys_blocks:
        return phys_blocks[letter1]
    raise SystemExit(
        f"letter1 {letter1!r} missing from virtual_phys_blocks.json and phys_block_map.json"
    )


def validate_carrier_map(
    carrier: dict[str, str],
    virtual: dict[str, dict],
    phys_blocks: dict[str, dict],
) -> None:
    empty = [k for k, v in carrier.items() if not v]
    if empty:
        raise SystemExit(f"empty letter2 for letter1: {', '.join(empty)}")
    missing_letter1 = [
        k for k in carrier if k not in virtual and k not in phys_blocks
    ]
    if missing_letter1:
        raise SystemExit(
            "letter1 missing from virtual_phys_blocks.json and phys_block_map.json: "
            + ", ".join(missing_letter1)
        )
    missing_letter2 = [v for v in carrier.values() if v and v not in phys_blocks]
    if missing_letter2:
        raise SystemExit(
            "letter2 not in phys_block_map.json: " + ", ".join(missing_letter2)
        )


def check_code_at(exe: bytes, off: int, expected_code: int, label: str) -> None:
    stored = struct.unpack_from("<I", exe, off)[0]
    if stored != expected_code:
        raise SystemExit(
            f"code mismatch at {label} 0x{off:X}: "
            f"expected 0x{expected_code:X}, got 0x{stored:X}"
        )


def patch_rect_metrics_tail(exe: bytearray, off: int, entry: dict) -> None:
    tail = parse_code(entry["tail"])
    exe[off + PHYS_OFF_RECT : off + PHYS_OFF_TAIL] = struct.pack(
        "<4H", entry["x"], entry["y"], entry["w"], entry["h"]
    )
    struct.pack_into("<I", exe, off + PHYS_OFF_TAIL, tail)
    exe[off + PHYS_OFF_METRICS : off + RECORD_SIZE] = struct.pack(
        "<6H", entry["m0"], entry["m1"], entry["m2"], 0, 0, 0
    )


def copy_rect_metrics_tail(exe: bytearray, src_off: int, dst_off: int) -> None:
    exe[dst_off + PHYS_OFF_RECT : dst_off + RECORD_SIZE] = exe[
        src_off + PHYS_OFF_RECT : src_off + RECORD_SIZE
    ]


def pick_free_kanji(used_carriers: set[str], stashed: set[str]) -> str:
    for ch in KANJI_100:
        if ch in used_carriers or ch in stashed:
            continue
        return ch
    raise SystemExit("no free kanji slot for rule 2 stash")


def apply_patches(
    exe: bytearray,
    carrier: dict[str, str],
    phys_blocks: dict[str, dict],
    virtual: dict[str, dict],
) -> dict[str, str]:
    resolved = dict(carrier)
    used_carriers = set(carrier.values())
    stashed_kanji: set[str] = set()

    for letter1, letter2 in carrier.items():
        ventry = resolve_glyph_entry(letter1, virtual, phys_blocks)
        if letter2 in KANJI_SET:
            block = phys_blocks[letter2]
            off = parse_off(block["phys_block_off"])
            code = parse_code(block["code"])
            check_code_at(exe, off, code, letter2)
            patch_rect_metrics_tail(exe, off, ventry)
            continue

        if letter2 in phys_blocks:
            block2 = phys_blocks[letter2]
            off2 = parse_off(block2["phys_block_off"])
            code2 = parse_code(block2["code"])
            check_code_at(exe, off2, code2, letter2)

            free_kanji = pick_free_kanji(used_carriers, stashed_kanji)
            stashed_kanji.add(free_kanji)
            block_k = phys_blocks[free_kanji]
            off_k = parse_off(block_k["phys_block_off"])
            code_k = parse_code(block_k["code"])
            check_code_at(exe, off_k, code_k, free_kanji)

            copy_rect_metrics_tail(exe, off2, off_k)
            patch_rect_metrics_tail(exe, off2, ventry)
            resolved[letter2] = free_kanji
            continue

        raise SystemExit(
            f"unsupported letter2 {letter2!r} for letter1 {letter1!r}: "
            f"not in phys_block_map.json"
        )

    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe-in", type=Path, default=DEFAULT_EXE_IN)
    parser.add_argument("--exe-out", type=Path, default=DEFAULT_EXE_OUT)
    parser.add_argument(
        "--force",
        action="store_true",
        default=True,
        help="rebuild JSON prerequisites and overwrite output (default: on)",
    )
    parser.add_argument(
        "--no-force",
        action="store_false",
        dest="force",
        help="reuse existing JSON if present",
    )
    args = parser.parse_args()

    exe_in = args.exe_in.resolve()
    exe_out = args.exe_out.resolve()

    if not exe_in.is_file():
        raise SystemExit(f"exe not found: {exe_in}")

    carrier, phys_blocks, virtual, _scan_range = load_maps(exe_in, force=args.force)
    validate_carrier_map(carrier, virtual, phys_blocks)

    exe = bytearray(exe_in.read_bytes())
    resolved = apply_patches(exe, carrier, phys_blocks, virtual)

    exe_out.parent.mkdir(parents=True, exist_ok=True)
    exe_out.write_bytes(exe)
    LETTER_CARRIER_MAP_RESOLVED_JSON.parent.mkdir(parents=True, exist_ok=True)
    LETTER_CARRIER_MAP_RESOLVED_JSON.write_text(
        json.dumps(resolved, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rule2_extra = len(resolved) - len(carrier)
    print(f"patched pairs: {len(carrier)}")
    print(f"rule 2 reloc entries: {rule2_extra}")
    print(f"wrote {exe_out}")
    print(f"wrote {LETTER_CARRIER_MAP_RESOLVED_JSON}")


if __name__ == "__main__":
    main()
