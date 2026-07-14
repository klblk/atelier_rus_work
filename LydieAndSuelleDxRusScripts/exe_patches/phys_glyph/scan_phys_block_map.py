#!/usr/bin/env python3
"""Scan vanilla exe phys blocks → phys_block_map.json."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

from kanji_carriers import KANJI_100
from phys_glyph_common import (
    DEFAULT_EXE_IN,
    PHYS_BLOCK_MAP_JSON,
    PHYS_BLOCK_MAP_MD,
    ROOT,
)

RECORD_SIZE = 28
PHYS_OFF_CODE = 0
PHYS_OFF_RECT = 4
PHYS_OFF_TAIL = 12
PHYS_OFF_METRICS = 16

ANCHOR_SEARCH_LO = 0xBC0000
ANCHOR_SEARCH_HI = 0xC30000
KANJI_REGION_LO = 0xC236E8
SCAN_HI = 0xC30000

DIGIT_ZERO_CODE = 0x30

EXTRA_PRINTABLE = frozenset("«»≥")


def code_to_short_letter(code: int) -> str | None:
    raw = code.to_bytes(4, "little").rstrip(b"\x00")
    if len(raw) not in (1, 2):
        return None
    try:
        ch = bytes(reversed(raw)).decode("utf-8")
    except UnicodeDecodeError:
        return None
    if len(ch) != 1:
        return None
    if ch in EXTRA_PRINTABLE:
        return ch
    if not ch.isprintable():
        return None
    return ch


def utf8_kanji_code(ch: str) -> int:
    if len(ch) != 1:
        raise ValueError(f"expected single character, got {ch!r}")
    b = bytes(reversed(ch.encode("utf-8")))
    return int.from_bytes(b + b"\x00" * (4 - len(b)), "little")


def code_to_kanji(code: int) -> str | None:
    if code <= 0xFFFF:
        return None
    raw = code.to_bytes(4, "little").rstrip(b"\x00")
    if len(raw) != 3:
        return None
    try:
        ch = bytes(reversed(raw)).decode("utf-8")
    except UnicodeDecodeError:
        return None
    if len(ch) != 1:
        return None
    if not (0x4E00 <= ord(ch) <= 0x9FFF):
        return None
    return ch


def read_phys_block(exe: bytes, p: int) -> dict | None:
    if p + RECORD_SIZE > len(exe):
        return None
    code = struct.unpack_from("<I", exe, p + PHYS_OFF_CODE)[0]
    x, y, w, h = struct.unpack_from("<4H", exe, p + PHYS_OFF_RECT)
    tail = struct.unpack_from("<I", exe, p + PHYS_OFF_TAIL)[0]
    m = struct.unpack_from("<6H", exe, p + PHYS_OFF_METRICS)
    if not (1 <= w <= 128 and 1 <= h <= 128):
        return None
    if x >= 4096 or y >= 4096:
        return None
    if m[0] > 200 or m[2] > 400:
        return None
    return {
        "code": code,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "m0": m[0],
        "m1": m[1],
        "m2": m[2],
        "tail": f"0x{tail:08X}",
        "phys_block_off": f"0x{p:X}",
    }


def block_entry(block: dict) -> dict:
    code = block["code"]
    hex_width = 8 if code > 0xFFFF else 4
    return {
        "code": f"0x{code:0{hex_width}X}",
        "x": block["x"],
        "y": block["y"],
        "w": block["w"],
        "h": block["h"],
        "m0": block["m0"],
        "m1": block["m1"],
        "m2": block["m2"],
        "tail": block["tail"],
        "phys_block_off": block["phys_block_off"],
    }


def find_digit_zero_anchor(exe: bytes) -> tuple[int, list[int]]:
    hits: list[int] = []
    for p in range(ANCHOR_SEARCH_LO, ANCHOR_SEARCH_HI - RECORD_SIZE, 4):
        if struct.unpack_from("<I", exe, p)[0] != DIGIT_ZERO_CODE:
            continue
        block = read_phys_block(exe, p)
        if block is None:
            continue
        hits.append(p)
    if not hits:
        raise SystemExit("Digit 0 phys block not found in exe")
    below_kanji = [p for p in hits if p < KANJI_REGION_LO]
    if below_kanji:
        anchor = max(below_kanji)
    else:
        anchor = min(hits, key=lambda p: abs(p - KANJI_REGION_LO))
    return anchor, sorted(hits)


def scan_short_codes(exe: bytes, scan_lo: int) -> dict[str, dict]:
    best: dict[int, tuple[str, dict]] = {}
    for p in range(scan_lo, SCAN_HI - RECORD_SIZE, 4):
        code = struct.unpack_from("<I", exe, p)[0]
        if code in best:
            continue
        letter = code_to_short_letter(code)
        if letter is None:
            continue
        block = read_phys_block(exe, p)
        if block is None:
            continue
        best[code] = (letter, block)
    out: dict[str, dict] = {}
    for _code, (letter, block) in sorted(best.items(), key=lambda kv: int(kv[1][1]["phys_block_off"], 16)):
        if letter in out:
            continue
        out[letter] = block_entry(block)
    return out


def lookup_kanji(exe: bytes, kanji: str, scan_lo: int) -> dict | None:
    code = utf8_kanji_code(kanji)
    for p in range(scan_lo, SCAN_HI - RECORD_SIZE, 4):
        if struct.unpack_from("<I", exe, p)[0] != code:
            continue
        if code_to_kanji(code) != kanji:
            continue
        block = read_phys_block(exe, p)
        if block is None:
            continue
        return block_entry(block)
    return None


def scan_kanji_list(exe: bytes, kanji_list: str, scan_lo: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ch in kanji_list:
        entry = lookup_kanji(exe, ch, scan_lo)
        if entry is None:
            print(f"warning: kanji {ch!r} not found in scan range", file=sys.stderr)
            continue
        out[ch] = entry
    return out


def write_md(
    path: Path,
    meta: dict,
    short_blocks: dict[str, dict],
    kanji_blocks: dict[str, dict],
    anchor_hits: list[int],
) -> None:
    lines = [
        "# Phys block map (vanilla exe)",
        "",
        f"Exe: `{meta['exe']}`",
        f"Table anchor (digit 0): `{meta['table_anchor']}` (all 0 hits: {', '.join(f'`0x{p:X}`' for p in anchor_hits)})",
        f"Latin table origin: `{meta['latin_table_origin']}`",
        f"Scan range: `{meta['scan_range'][0]}`–`{meta['scan_range'][1]}`",
        "",
        f"Short-code blocks: **{len(short_blocks)}**",
        f"Kanji blocks (hardcoded 100): **{len(kanji_blocks)}**",
        "",
        "## Short-code (first 20 by phys_block_off)",
        "",
        "| letter | code | phys_block | m0 | m2 | w×h |",
        "|--------|------|------------|-----|-----|-----|",
    ]
    short_sorted = sorted(short_blocks.items(), key=lambda kv: int(kv[1]["phys_block_off"], 16))
    for letter, b in short_sorted[:20]:
        lines.append(
            f"| {letter} | {b['code']} | {b['phys_block_off']} | {b['m0']} | {b['m2']} | {b['w']}×{b['h']} |"
        )
    lines.extend(
        [
            "",
            "## Kanji (first 10)",
            "",
            "| kanji | code | phys_block | m0 | m2 |",
            "|-------|------|------------|-----|-----|",
        ]
    )
    kanji_sorted = sorted(kanji_blocks.items(), key=lambda kv: int(kv[1]["phys_block_off"], 16))
    for ch, b in kanji_sorted[:10]:
        lines.append(
            f"| {ch} | {b['code']} | {b['phys_block_off']} | {b['m0']} | {b['m2']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan_phys_block_map(
    exe_path: Path,
    *,
    out_json: Path = PHYS_BLOCK_MAP_JSON,
    out_md: Path = PHYS_BLOCK_MAP_MD,
) -> None:
    if not exe_path.is_file():
        raise SystemExit(f"exe not found: {exe_path}")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    exe = exe_path.read_bytes()

    anchor, anchor_hits = find_digit_zero_anchor(exe)
    scan_lo = anchor
    latin_table_origin = anchor

    short_blocks = scan_short_codes(exe, scan_lo)
    kanji_blocks = scan_kanji_list(exe, KANJI_100, scan_lo)

    blocks: dict[str, dict] = dict(short_blocks)
    for ch, entry in kanji_blocks.items():
        blocks[ch] = entry

    try:
        exe_rel = str(exe_path.resolve().relative_to(ROOT))
    except ValueError:
        exe_rel = str(exe_path.resolve())

    meta = {
        "exe": exe_rel,
        "table_anchor": f"0x{anchor:X}",
        "table_anchor_hits": [f"0x{p:X}" for p in anchor_hits],
        "latin_table_origin": f"0x{latin_table_origin:X}",
        "kanji_region_lo": f"0x{KANJI_REGION_LO:X}",
        "scan_range": [f"0x{scan_lo:X}", f"0x{SCAN_HI:X}"],
        "stride_bytes": RECORD_SIZE,
        "short_code_count": len(short_blocks),
        "kanji_count": len(kanji_blocks),
        "total_block_count": len(blocks),
    }

    payload = {"meta": meta, "blocks": blocks}
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md(out_md, meta, short_blocks, kanji_blocks, anchor_hits)

    print(f"table anchor (digit 0): 0x{anchor:X}")
    print(f"latin table origin: 0x{latin_table_origin:X}")
    print(f"short-code blocks: {len(short_blocks)}")
    print(f"kanji blocks: {len(kanji_blocks)} / {len(KANJI_100)}")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE_IN, help="vanilla exe to scan")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing output (default behavior when invoked from patch flow)",
    )
    args = parser.parse_args()
    scan_phys_block_map(args.exe.resolve())


if __name__ == "__main__":
    main()
