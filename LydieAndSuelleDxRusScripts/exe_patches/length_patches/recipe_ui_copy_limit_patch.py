#!/usr/bin/env python3
"""Patch recipe condition UI copy limits in Atelier Lydie & Suelle DX exe.

WinDbg:
- v2 (work/errors/quality_str_error/windbg_v2.txt): cluster A +0x4136AA -> +0xa9a0
- v3 (work/errors/quality_str_error/windbg_v3.txt): cluster B +0x3E5D4A -> +0xa9a0
- Both: +0x85ad18 -> +0x85C0D7; mov edx,32/64; RU 6619426 = 33 B > 32

Two mirror clusters, mov edx before call +0xa9a0 for str_ui 6619426–6619429.
"""

from __future__ import annotations

_TEXT_RAW = 0x400
_TEXT_VA = 0x140001000


def va_to_file_offset(va: int) -> int:
    return _TEXT_RAW + (va - _TEXT_VA)


RECIPE_COPY_LIMIT_32 = 32
RECIPE_COPY_LIMIT_64 = 64
RECIPE_COPY_LIMIT_PATCHED = 128

_MOV_EDX_32 = bytes([0xBA, 0x20, 0x00, 0x00, 0x00])
_MOV_EDX_64 = bytes([0xBA, 0x40, 0x00, 0x00, 0x00])
_MOV_EDX_128 = bytes([0xBA, 0x80, 0x00, 0x00, 0x00])

PatchEntry = tuple[str, int, bytes, bytes, int, int]

_RECIPE_CLUSTER_A_PATCHES: list[PatchEntry] = [
    (
        "mov edx, 32 -> 128 (6619426 Quality, cluster A)",
        0x1404136A5,
        _MOV_EDX_32,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_32,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
    (
        "mov edx, 64 -> 128 (6619427 Effects, cluster A)",
        0x14041372E,
        _MOV_EDX_64,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_64,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
    (
        "mov edx, 64 -> 128 (6619428 Traits, cluster A)",
        0x1404137DC,
        _MOV_EDX_64,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_64,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
    (
        "mov edx, 64 -> 128 (6619429 Components, cluster A)",
        0x140413882,
        _MOV_EDX_64,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_64,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
]

_RECIPE_CLUSTER_B_PATCHES: list[PatchEntry] = [
    (
        "mov edx, 32 -> 128 (6619426 Quality, cluster B)",
        0x1403E5D45,
        _MOV_EDX_32,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_32,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
    (
        "mov edx, 64 -> 128 (6619427 Effects, cluster B)",
        0x1403E5DDD,
        _MOV_EDX_64,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_64,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
    (
        "mov edx, 64 -> 128 (6619428 Traits, cluster B)",
        0x1403E5E85,
        _MOV_EDX_64,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_64,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
    (
        "mov edx, 64 -> 128 (6619429 Components, cluster B)",
        0x1403E5F25,
        _MOV_EDX_64,
        _MOV_EDX_128,
        RECIPE_COPY_LIMIT_64,
        RECIPE_COPY_LIMIT_PATCHED,
    ),
]

_RECIPE_FIXED_PATCHES: list[PatchEntry] = _RECIPE_CLUSTER_A_PATCHES + _RECIPE_CLUSTER_B_PATCHES


def apply_recipe_ui_copy_limit_patch(exe: bytearray) -> list[dict]:
    vanilla = bytes(exe)
    applied: list[dict] = []

    for desc, va, old, new, limit_vanilla, limit_patched in _RECIPE_FIXED_PATCHES:
        if len(old) != len(new):
            raise ValueError(f"{desc}: old/new length mismatch")
        fo = va_to_file_offset(va)
        got = bytes(exe[fo : fo + len(old)])
        if got != old:
            raise ValueError(
                f"{desc}: expected {old.hex()} at file 0x{fo:X} (va 0x{va:X}), got {got.hex()}"
            )
        exe[fo : fo + len(new)] = new
        applied.append(
            {
                "site": desc,
                "file_offset": f"0x{fo:X}",
                "va": f"0x{va:X}",
                "from_hex": old.hex(),
                "to_hex": new.hex(),
                "limit_vanilla": limit_vanilla,
                "limit_patched": limit_patched,
            }
        )
    return applied
