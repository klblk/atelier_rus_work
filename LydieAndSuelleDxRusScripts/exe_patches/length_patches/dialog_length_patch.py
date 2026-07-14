#!/usr/bin/env python3
"""Patch dialog string buffer limit in Atelier Lydie & Suelle DX exe (256 -> 512).

WinDbg:
- v1: AV @ +0x843F59 — memset 512 B into frame 0x138
- v2: frame cluster but missed second epilogue @ +0x303192 → load crash @ +0x30319A
- Vanilla: FAST_FAIL @ +0x85C0D7 for 257 B string

v3: v2 + second epilogue add rsp @ +0x30318F, lea rax [rsp+0x170] @ +0x303149.
Hot fn +0x303020..+0x3031A0: sub/add rsp 0x138->0x270, slots, mov r8d 256->512.
Buffer stays @ rsp+0x30 (disp8).
"""

from __future__ import annotations

import struct

_TEXT_RAW = 0x400
_TEXT_VA = 0x140001000


def va_to_file_offset(va: int) -> int:
    return _TEXT_RAW + (va - _TEXT_VA)


DIALOG_BUF_MAX_VANILLA = 256
DIALOG_BUF_MAX_PATCHED = 512

DIALOG_MSG_MAX_VANILLA = DIALOG_BUF_MAX_VANILLA
DIALOG_MSG_MAX_PATCHED = DIALOG_BUF_MAX_PATCHED

_FRAME_VANILLA = 0x138
_FRAME_PATCHED = 0x270

_SLOT_OLD = 0x130
_SLOT_NEW = 0x268
_LEA_RSP170_OLD = 0x170
_LEA_RSP170_NEW = 0x2A8

_HOT_FN_START = 0x140303020
_HOT_FN_END = 0x1403031A0

_MOV_R8D_256 = bytes([0x41, 0xB8, 0x00, 0x01, 0x00, 0x00])
_MOV_R8D_512 = bytes([0x41, 0xB8, 0x00, 0x02, 0x00, 0x00])

_LEA_RSP170_PREFIXES: tuple[tuple[bytes, str], ...] = (
    (bytes([0x48, 0x8D, 0x9C, 0x24]), "rbx"),
    (bytes([0x48, 0x8D, 0x84, 0x24]), "rax"),
)

PatchEntry = tuple[str, int, bytes, bytes, int, int]


def _imm32_le(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def _collect_hot_fn_slot_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    """[rsp+0x130] and lea reg,[rsp+0x170] in dialog fn (+0x303020..+0x3031A0)."""
    fo = va_to_file_offset(_HOT_FN_START)
    end_fo = va_to_file_offset(_HOT_FN_END)
    chunk = exe[fo:end_fo]
    base = _HOT_FN_START
    patches: list[PatchEntry] = []

    for i in range(3, len(chunk) - 4):
        if chunk[i - 1] != 0x24:
            continue
        imm = struct.unpack("<I", chunk[i : i + 4])[0]
        va = base + i
        if va in seen:
            continue

        if imm == _SLOT_OLD:
            seen.add(va)
            new_imm = _SLOT_NEW
            patches.append(
                (
                    f"[rsp+{_SLOT_OLD:#x}] -> [rsp+{new_imm:#x}]",
                    va,
                    _imm32_le(imm),
                    _imm32_le(new_imm),
                    _SLOT_OLD,
                    new_imm,
                )
            )
            continue

        if imm != _LEA_RSP170_OLD:
            continue

        for prefix, reg in _LEA_RSP170_PREFIXES:
            if chunk[i - 4 : i] == prefix:
                seen.add(va)
                patches.append(
                    (
                        f"lea {reg}, [rsp+{_LEA_RSP170_OLD:#x}] -> [rsp+{_LEA_RSP170_NEW:#x}]",
                        va,
                        _imm32_le(imm),
                        _imm32_le(_LEA_RSP170_NEW),
                        _LEA_RSP170_OLD,
                        _LEA_RSP170_NEW,
                    )
                )
                break

    return patches


_DIALOG_FIXED_PATCHES: list[PatchEntry] = [
    (
        f"sub rsp, {_FRAME_VANILLA:#x} -> {_FRAME_PATCHED:#x}",
        0x140303035,
        _imm32_le(_FRAME_VANILLA),
        _imm32_le(_FRAME_PATCHED),
        _FRAME_VANILLA,
        _FRAME_PATCHED,
    ),
    (
        f"add rsp, {_FRAME_VANILLA:#x} -> {_FRAME_PATCHED:#x} (epilogue 1)",
        0x14030313C,
        _imm32_le(_FRAME_VANILLA),
        _imm32_le(_FRAME_PATCHED),
        _FRAME_VANILLA,
        _FRAME_PATCHED,
    ),
    (
        f"add rsp, {_FRAME_VANILLA:#x} -> {_FRAME_PATCHED:#x} (epilogue 2)",
        0x140303192,
        _imm32_le(_FRAME_VANILLA),
        _imm32_le(_FRAME_PATCHED),
        _FRAME_VANILLA,
        _FRAME_PATCHED,
    ),
    (
        "mov r8d, 256 -> 512 (dialog copy path 1)",
        0x140303068,
        _MOV_R8D_256,
        _MOV_R8D_512,
        DIALOG_BUF_MAX_VANILLA,
        DIALOG_BUF_MAX_PATCHED,
    ),
    (
        "mov r8d, 256 -> 512 (dialog copy path 2)",
        0x140303094,
        _MOV_R8D_256,
        _MOV_R8D_512,
        DIALOG_BUF_MAX_VANILLA,
        DIALOG_BUF_MAX_PATCHED,
    ),
]


def _all_patches(exe: bytes) -> list[PatchEntry]:
    seen: set[int] = set()
    slot_patches = _collect_hot_fn_slot_patches(exe, seen)
    all_p = _DIALOG_FIXED_PATCHES + slot_patches
    all_p.sort(key=lambda item: item[1])
    return all_p


def apply_dialog_length_patch(exe: bytearray) -> list[dict]:
    vanilla = bytes(exe)
    applied: list[dict] = []

    for desc, va, old, new, limit_vanilla, limit_patched in _all_patches(vanilla):
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
