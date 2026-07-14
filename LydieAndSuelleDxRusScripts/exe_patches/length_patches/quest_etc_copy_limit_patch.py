#!/usr/bin/env python3
"""Patch quest objective UI copy limit in Atelier Lydie & Suelle DX exe.

WinDbg work/errors/unknow_error/windbg_v1.txt:
- CRT FAST_FAIL @ +0x85c0d7, caller +0x3A1E1, String_No 4980738 (Obtain %s.)
- Same path covers 4980737 (Defeat %s.)

v6 (partial shift, same-size):
- Frame sub/add rsp 0x80 -> 0xC0
- Main string buffer 64 B @ [rbp-0x40] -> 128 B @ [rbp-0x80]
- Struct meta @ [rbp-0x38..-0x08] unchanged
- Alt-path init via rcx=[rbp-0x80], movaps [rcx-0x20] (same-size)
- Read path lea rdx -> [rbp-0x80] (write/read match)

v6.1 (rsp restore slots, windbg_v3):
- Frame grew 0x80 -> 0xC0 but mov reg,[rsp+disp] imm32 stayed vanilla
- rbx restored from [rsp+0xA0] instead of [rsp+0xE0] -> AV @ +0x3A6A0 (rbx=0)
- 4 same-size imm32 patches (+0x40 shift) for r12/r14/rsi/rbx restore

Rollback: revert to v2 (2 sites) if regressions appear.
"""

from __future__ import annotations

import struct

_TEXT_RAW = 0x400
_TEXT_VA = 0x140001000

QUEST_COPY_LIMIT_64 = 64
QUEST_COPY_LIMIT_PATCHED = 128

_FRAME_VANILLA = 0x80
_FRAME_PATCHED = 0xC0

_RSP_SLOT_SHIFT = 0x40

_RSP_RESTORE_SITES: tuple[tuple[str, int, int, int], ...] = (
    ("mov r12,[rsp+...]", 0x14003A215, 0xB0, 0xF0),
    ("mov r14,[rsp+...]", 0x14003A3CA, 0xB8, 0xF8),
    ("mov rsi,[rsp+...]", 0x14003A3D2, 0xA8, 0xE8),
    ("mov rbx,[rsp+...]", 0x14003A3DA, 0xA0, 0xE0),
)

_MOV_EDX_64 = bytes([0xBA, 0x40, 0x00, 0x00, 0x00])
_MOV_EDX_128 = bytes([0xBA, 0x80, 0x00, 0x00, 0x00])

_PATH_A_VA = 0x14003A238
_PATH_A_OLD_LEN = 0x14003A285 - _PATH_A_VA
_PATH_A_NEW = bytes(
    [
        0x48,
        0x8D,
        0x4D,
        0x80,  # lea rcx,[rbp-0x80]
        0x0F,
        0x57,
        0xC0,  # xorps xmm0,xmm0
        0x0F,
        0x29,
        0x41,
        0xE0,  # movaps [rcx-0x20],xmm0
        0x0F,
        0x29,
        0x41,
        0xF0,  # movaps [rcx-0x10],xmm0
        0xB9,
        0x37,
        0x00,
        0x65,
        0x00,
        0xE8,
        0x72,
        0xA0,
        0x1F,
        0x00,
        0x4C,
        0x8B,
        0xC0,
        0x48,
        0x8D,
        0x49,
        0xE0,  # lea rcx,[rcx-0x20]
        0x45,
        0x8B,
        0xCE,
        0xBA,
        0x20,
        0x00,
        0x00,
        0x00,
        0xE8,
        0x2E,
        0x07,
        0xFD,
        0xFF,
        0x4A,
        0x8B,
        0x4C,
        0xFF,
        0x58,
        0x48,
        0x8B,
        0xD1,
        0x90,
        0xE8,
        0x20,
        0x88,
        0x30,
        0x00,
    ]
    + [0x90] * 13
    + [0xE9, 0x88, 0x00, 0x00, 0x00]
)

_PATH_B_VA = 0x14003A2A1
_PATH_B_OLD_LEN = 0x14003A301 - _PATH_B_VA
_PATH_B_NEW = bytes(
    [
        0x48,
        0x8D,
        0x4D,
        0x80,
        0x0F,
        0x57,
        0xC0,
        0x0F,
        0x29,
        0x41,
        0xE0,
        0x0F,
        0x29,
        0x41,
        0xF0,
        0x45,
        0x8B,
        0xCE,
        0x4C,
        0x8D,
        0x05,
        0xBF,
        0xC9,
        0x94,
        0x00,
        0x48,
        0x8D,
        0x49,
        0xE0,
        0x33,
        0xC0,
        0x8D,
        0x50,
        0x10,
        0xE8,
        0xD5,
        0x06,
        0xFD,
        0xFF,
        0x4A,
        0x8B,
        0x4C,
        0xFF,
        0x58,
        0x48,
        0x8D,
        0x15,
        0xA1,
        0xC9,
        0x94,
        0x00,
        0x41,
        0x83,
        0xC8,
        0xFF,
        0xE8,
        0xB0,
        0xEE,
        0x2F,
        0x00,
        0x48,
        0x85,
        0xC0,
        0x74,
        0x28,
        0x48,
        0x8B,
        0x10,
        0x48,
        0x8B,
        0xC8,
        0xFF,
        0x52,
        0x50,
        0x48,
        0x85,
        0xC0,
        0x74,
        0x1A,
        0x48,
        0x8D,
        0x95,
        0x60,
        0xFF,
        0xFF,
        0xFF,  # lea rdx,[rbp-0xA0] disp32 (7 B fusion)
        0x48,
        0x8B,
        0xC8,
        0xE8,
        0xA1,
        0x87,
        0x30,
        0x00,
        0xEB,
        0x0C,
    ]
)

assert len(_PATH_A_NEW) == _PATH_A_OLD_LEN
assert len(_PATH_B_NEW) == _PATH_B_OLD_LEN

_STRUCT_META_START = 0x14003A178
_STRUCT_META_END = 0x14003A194

PatchSite = tuple[str, int, bytes, bytes, tuple[bytes, ...], str | None]


_FRAME_SITES: tuple[tuple[str, int], ...] = (
    ("sub rsp", 0x14003A0AA),
    ("add rsp epilogue 1", 0x14003A3ED),
    ("add rsp epilogue 2", 0x14003A402),
    ("add rsp epilogue 3", 0x14003A410),
)

_CORE_SITES: tuple[PatchSite, ...] = (
    (
        "mov [rbp-0x40] -> [rbp-0x80] struct[0]",
        0x14003A174,
        bytes([0x48, 0x89, 0x45, 0xC0]),
        bytes([0x48, 0x89, 0x45, 0x80]),
        (bytes([0x48, 0x89, 0x45, 0x80]),),
        "buffer_write",
    ),
    (
        "lea rcx,[rbp-0x40] -> [rbp-0x80] copy dest",
        0x14003A1D0,
        bytes([0x48, 0x8D, 0x4D, 0xC0]),
        bytes([0x48, 0x8D, 0x4D, 0x80]),
        (bytes([0x48, 0x8D, 0x4D, 0x80]),),
        "buffer_write",
    ),
    (
        "mov edx, 64 -> 128",
        0x14003A1D7,
        _MOV_EDX_64,
        _MOV_EDX_128,
        (_MOV_EDX_128,),
        "copy_limit",
    ),
    (
        "lea rdx,[rbp-0x40] -> [rbp-0x80] read path",
        0x14003A312,
        bytes([0x48, 0x8D, 0x55, 0xC0]),
        bytes([0x48, 0x8D, 0x55, 0x80]),
        (bytes([0x48, 0x8D, 0x55, 0x80]),),
        "buffer_read",
    ),
)

_BLOCK_SITES: tuple[tuple[str, int, int, bytes], ...] = (
    ("path A alt init xmm/rcx-relative", _PATH_A_VA, _PATH_A_OLD_LEN, _PATH_A_NEW),
    ("path B alt init xmm/rcx-relative", _PATH_B_VA, _PATH_B_OLD_LEN, _PATH_B_NEW),
)


def va_to_file_offset(va: int) -> int:
    return _TEXT_RAW + (va - _TEXT_VA)


def _is_v6_frame_patched(exe: bytes) -> bool:
    fo = va_to_file_offset(0x14003A0AA)
    return exe[fo + 3 : fo + 7] == struct.pack("<I", _FRAME_PATCHED)


def _is_v61_patched(exe: bytes) -> bool:
    if not _is_v6_frame_patched(exe):
        return False
    fo = va_to_file_offset(0x14003A3DA)
    return exe[fo : fo + 4] == struct.pack("<I", 0xE0)


def _apply_site(
    exe: bytearray,
    *,
    desc: str,
    va: int,
    old: bytes,
    new: bytes,
    already: tuple[bytes, ...],
    meta_key: str | None,
    limit_vanilla: int | None = None,
    limit_patched: int | None = None,
) -> dict | None:
    if len(old) != len(new):
        raise ValueError(f"{desc}: old/new length mismatch ({len(old)} vs {len(new)})")
    fo = va_to_file_offset(va)
    got = bytes(exe[fo : fo + len(old)])
    if got == new or got in already:
        return None
    if got != old:
        raise ValueError(
            f"{desc}: expected {old.hex()} at file 0x{fo:X} (va 0x{va:X}), got {got.hex()}"
        )
    exe[fo : fo + len(new)] = new
    entry: dict = {
        "site": desc,
        "file_offset": f"0x{fo:X}",
        "va": f"0x{va:X}",
        "from_hex": old.hex(),
        "to_hex": new.hex(),
    }
    if meta_key == "copy_limit":
        entry["limit_vanilla"] = limit_vanilla
        entry["limit_patched"] = limit_patched
    if meta_key in ("buffer_write", "buffer_read", "copy_limit"):
        entry["buffer"] = "[rbp-0x80]"
    return entry


def _apply_frame_sites(exe: bytearray) -> list[dict]:
    applied: list[dict] = []
    for label, va in _FRAME_SITES:
        fo = va_to_file_offset(va)
        old = struct.unpack_from("<I", exe, fo + 3)[0]
        if old == _FRAME_PATCHED:
            continue
        if old != _FRAME_VANILLA:
            raise ValueError(
                f"{label}: expected frame {_FRAME_VANILLA:#x}, got {old:#x} @ 0x{va:X}"
            )
        struct.pack_into("<I", exe, fo + 3, _FRAME_PATCHED)
        applied.append(
            {
                "site": f"{label} {_FRAME_VANILLA:#x} -> {_FRAME_PATCHED:#x}",
                "file_offset": f"0x{fo + 3:X}",
                "va": f"0x{va + 3:X}",
                "from_hex": f"{_FRAME_VANILLA:08x}",
                "to_hex": f"{_FRAME_PATCHED:08x}",
            }
        )
    return applied


def _apply_rsp_restore_sites(exe: bytearray) -> list[dict]:
    applied: list[dict] = []
    for desc, va_imm, old_imm, new_imm in _RSP_RESTORE_SITES:
        fo = va_to_file_offset(va_imm)
        got = struct.unpack_from("<I", exe, fo)[0]
        if got == new_imm:
            continue
        if got != old_imm:
            raise ValueError(
                f"{desc}: expected imm32 {old_imm:#x}, got {got:#x} @ va 0x{va_imm:X}"
            )
        struct.pack_into("<I", exe, fo, new_imm)
        applied.append(
            {
                "site": f"{desc} {old_imm:#x} -> {new_imm:#x}",
                "file_offset": f"0x{fo:X}",
                "va": f"0x{va_imm:X}",
                "from_hex": f"{old_imm:08x}",
                "to_hex": f"{new_imm:08x}",
            }
        )
    return applied


def _apply_block_site(
    exe: bytearray,
    *,
    desc: str,
    va: int,
    old_len: int,
    new: bytes,
) -> dict | None:
    fo = va_to_file_offset(va)
    old = bytes(exe[fo : fo + old_len])
    if old == new:
        return None
    if len(new) != old_len:
        raise ValueError(f"{desc}: block length mismatch ({old_len} vs {len(new)})")
    exe[fo : fo + old_len] = new
    return {
        "site": desc,
        "file_offset": f"0x{fo:X}",
        "va": f"0x{va:X}",
        "from_hex": old.hex(),
        "to_hex": new.hex(),
        "buffer": "[rbp-0x80]/[rcx-0x20]",
    }


def _verify_struct_meta(exe: bytes, vanilla: bytes) -> None:
    fo_start = va_to_file_offset(_STRUCT_META_START)
    fo_end = va_to_file_offset(_STRUCT_META_END)
    if exe[fo_start:fo_end] != vanilla[fo_start:fo_end]:
        raise ValueError("struct meta @ [rbp-0x38..-0x08] was modified")


def apply_quest_etc_copy_limit_patch(exe: bytearray) -> list[dict]:
    if _is_v61_patched(exe):
        return []

    vanilla = bytes(exe)
    applied: list[dict] = []

    applied.extend(_apply_frame_sites(exe))

    for desc, va, old, new, already, meta_key in _CORE_SITES:
        entry = _apply_site(
            exe,
            desc=desc,
            va=va,
            old=old,
            new=new,
            already=already,
            meta_key=meta_key,
            limit_vanilla=QUEST_COPY_LIMIT_64,
            limit_patched=QUEST_COPY_LIMIT_PATCHED,
        )
        if entry is not None:
            applied.append(entry)

    for desc, va, old_len, new in _BLOCK_SITES:
        entry = _apply_block_site(exe, desc=desc, va=va, old_len=old_len, new=new)
        if entry is not None:
            applied.append(entry)

    applied.extend(_apply_rsp_restore_sites(exe))

    _verify_struct_meta(exe, vanilla)
    return applied
