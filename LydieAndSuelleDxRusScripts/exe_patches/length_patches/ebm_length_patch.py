#!/usr/bin/env python3
"""Patch EBM event message buffer limit in Atelier Lydie & Suelle DX exe (400 -> 800).

WinDbg stacks (work/errors/ebm_over_400_crash*):
- v1: mov r9d,400 in +0x1DD9C0 string copy path
- v2: sub rsp without lea r11; 405 B overwrite [rsp+0x1C0]
- v3: incomplete cluster patch -> WIL assert in std::string path
- v4: erroneous add rdx,0x1A0 patch + add reg,0x1C0 outside scan range -> C++ throw
- v5: cluster OK (copy len=800) but WIL @ +0x42322D reserve arg 0x3B0 (944)

Patches the EBM loader block +0x1DD000..+0x1DF000: copy limit, frame size,
[rsp+slot] shifts, [rbx+8] pointer adjustments, imul/add-reg strides, end offset.
v6: string layer +0x1DD580..+0x1DDE20 add/lea [reg+0x1A0] -> +0x320 (not +0x340).
v7: +12 explicit gap sites (vector growth, helpers +0x1DD0F0/+0x1DD1D0, copy loop +0x1DE020)
missed by v6 collectors — see work/errors/ebm_new_error/ (qc07_rog AV @ +0x94CE75).
Does NOT patch +0x42322D std::string path.
"""

from __future__ import annotations

import struct

_TEXT_RAW = 0x400
_TEXT_VA = 0x140001000


def va_to_file_offset(va: int) -> int:
    return _TEXT_RAW + (va - _TEXT_VA)


EBM_BUF_MAX_VANILLA = 400
EBM_BUF_MAX_PATCHED = 800

EBM_MSG_MAX_VANILLA = EBM_BUF_MAX_VANILLA
EBM_MSG_MAX_PATCHED = EBM_BUF_MAX_PATCHED

_FRAME_VANILLA = 0x1E0
_FRAME_PATCHED = 0x3A0
_STACK_SLOT_SHIFT = 0x180
_SLOT_OLD = 0x1C0
_SLOT_NEW = 0x340
_END_OFFSET_OLD = 0x198
_END_OFFSET_NEW = 0x328

_STRUCT_OFFSET_1A0_OLD = 0x1A0
_STRUCT_OFFSET_1A0_NEW = 0x320
_STRUCT_OFFSET_1B0_OLD = 0x1B0
_STRUCT_OFFSET_1B0_NEW = 0x330
_STRUCT_OFFSET_1B8_OLD = 0x1B8
_STRUCT_OFFSET_1B8_NEW = 0x338

_STRING_LAYER_START = 0x1401DD580
_STRING_LAYER_END = 0x1401DDE20

_STACK_SLOTS = (0x1C0, 0x1C8, 0x1D0, 0x210)

_EBM_CLUSTER_START = 0x1401DD000
_EBM_CLUSTER_END = 0x1401DF000

_REG_NAMES = ("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi")

PatchEntry = tuple[str, int, bytes, bytes, int, int]


def _imm32_le(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def _imm32_signed(value: int) -> bytes:
    return struct.pack("<i", value)


def _cluster_chunk(exe: bytes) -> tuple[bytes, int]:
    start = va_to_file_offset(_EBM_CLUSTER_START)
    end = va_to_file_offset(_EBM_CLUSTER_END)
    return exe[start:end], _EBM_CLUSTER_START


def _collect_rsp_slot_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    chunk, base = _cluster_chunk(exe)
    patches: list[PatchEntry] = []

    for i in range(3, len(chunk) - 4):
        if chunk[i - 1] != 0x24:
            continue
        imm = struct.unpack("<I", chunk[i : i + 4])[0]
        if imm not in _STACK_SLOTS:
            continue
        va = base + i
        if va in seen:
            continue
        seen.add(va)
        new_imm = imm + _STACK_SLOT_SHIFT
        patches.append(
            (
                f"[rsp+{imm:#x}] -> [rsp+{new_imm:#x}]",
                va,
                _imm32_le(imm),
                _imm32_le(new_imm),
                imm,
                new_imm,
            )
        )
    return patches


def _collect_rbx8_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    chunk, base = _cluster_chunk(exe)
    patches: list[PatchEntry] = []

    for i in range(len(chunk) - 8):
        if chunk[i : i + 4] != bytes([0x48, 0x81, 0x43, 0x08]):
            continue
        imm = struct.unpack("<i", chunk[i + 4 : i + 8])[0]
        if imm not in (_SLOT_OLD, -_SLOT_OLD):
            continue
        va = base + i + 4
        if va in seen:
            continue
        seen.add(va)
        new_imm = _SLOT_NEW if imm > 0 else -_SLOT_NEW
        patches.append(
            (
                f"add [rbx+8], {imm:#x} -> {new_imm:#x}",
                va,
                _imm32_signed(imm),
                _imm32_signed(new_imm),
                abs(imm),
                abs(new_imm),
            )
        )
    return patches


def _collect_imul_stride_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    chunk, base = _cluster_chunk(exe)
    patches: list[PatchEntry] = []

    for i in range(len(chunk) - 6):
        if chunk[i] != 0x69:
            continue
        imm = struct.unpack("<I", chunk[i + 2 : i + 6])[0]
        if imm != _SLOT_OLD:
            continue
        va = base + i + 2
        if va in seen:
            continue
        seen.add(va)
        patches.append(
            (
                f"imul stride {_SLOT_OLD:#x} -> {_SLOT_NEW:#x}",
                va,
                _imm32_le(_SLOT_OLD),
                _imm32_le(_SLOT_NEW),
                _SLOT_OLD,
                _SLOT_NEW,
            )
        )
    return patches


def _collect_add_reg_stride_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    """add reg, 0x1C0 via 48 81 C0..C7 (excludes add [rbx+8] handled separately)."""
    chunk, base = _cluster_chunk(exe)
    patches: list[PatchEntry] = []

    for i in range(len(chunk) - 7):
        if chunk[i] != 0x48 or chunk[i + 1] != 0x81:
            continue
        modrm = chunk[i + 2]
        if modrm < 0xC0 or modrm > 0xC7:
            continue
        imm = struct.unpack("<I", chunk[i + 3 : i + 7])[0]
        if imm != _SLOT_OLD:
            continue
        va = base + i + 3
        if va in seen:
            continue
        seen.add(va)
        reg = _REG_NAMES[modrm - 0xC0]
        patches.append(
            (
                f"add {reg}, {_SLOT_OLD:#x} -> {_SLOT_NEW:#x}",
                va,
                _imm32_le(_SLOT_OLD),
                _imm32_le(_SLOT_NEW),
                _SLOT_OLD,
                _SLOT_NEW,
            )
        )
    return patches


def _collect_end_offset_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    """lea rdx, [rdi+0x198] -> [rdi+0x328] (400+8 -> 800+8 end-of-data offset)."""
    chunk, base = _cluster_chunk(exe)
    patches: list[PatchEntry] = []

    for i in range(len(chunk) - 7):
        if chunk[i : i + 3] != bytes([0x48, 0x8D, 0x97]):
            continue
        imm = struct.unpack("<I", chunk[i + 3 : i + 7])[0]
        if imm != _END_OFFSET_OLD:
            continue
        va = base + i + 3
        if va in seen:
            continue
        seen.add(va)
        patches.append(
            (
                f"lea rdx, [rdi+{_END_OFFSET_OLD:#x}] -> [rdi+{_END_OFFSET_NEW:#x}]",
                va,
                _imm32_le(_END_OFFSET_OLD),
                _imm32_le(_END_OFFSET_NEW),
                _END_OFFSET_OLD,
                _END_OFFSET_NEW,
            )
        )
    return patches


def _collect_string_layer_1a0_patches(exe: bytes, seen: set[int]) -> list[PatchEntry]:
    """add/lea [reg+0x1A0] in string pipeline only (+0x1DD580..+0x1DDE20)."""
    fo = va_to_file_offset(_STRING_LAYER_START)
    end_fo = va_to_file_offset(_STRING_LAYER_END)
    chunk = exe[fo:end_fo]
    base = _STRING_LAYER_START
    patches: list[PatchEntry] = []

    for i in range(len(chunk) - 7):
        va_imm = base + i + 3
        if va_imm in seen:
            continue

        # add rdx, imm32
        if chunk[i : i + 3] == bytes([0x48, 0x81, 0xC2]):
            imm = struct.unpack("<I", chunk[i + 3 : i + 7])[0]
            if imm != _STRUCT_OFFSET_1A0_OLD:
                continue
            seen.add(va_imm)
            patches.append(
                (
                    f"add rdx, {_STRUCT_OFFSET_1A0_OLD:#x} -> {_STRUCT_OFFSET_1A0_NEW:#x} (string layer)",
                    va_imm,
                    _imm32_le(_STRUCT_OFFSET_1A0_OLD),
                    _imm32_le(_STRUCT_OFFSET_1A0_NEW),
                    _STRUCT_OFFSET_1A0_OLD,
                    _STRUCT_OFFSET_1A0_NEW,
                )
            )
            continue

        # lea reg, [reg+imm32]: 48 8d /r
        if chunk[i : i + 2] != bytes([0x48, 0x8D]):
            continue
        imm = struct.unpack("<I", chunk[i + 3 : i + 7])[0]
        if imm != _STRUCT_OFFSET_1A0_OLD:
            continue
        modrm = chunk[i + 2]
        seen.add(va_imm)
        dest = _REG_NAMES[(modrm >> 3) & 7]
        patches.append(
            (
                f"lea {dest}, [+{_STRUCT_OFFSET_1A0_OLD:#x}] -> [+{_STRUCT_OFFSET_1A0_NEW:#x}] (string layer)",
                va_imm,
                _imm32_le(_STRUCT_OFFSET_1A0_OLD),
                _imm32_le(_STRUCT_OFFSET_1A0_NEW),
                _STRUCT_OFFSET_1A0_OLD,
                _STRUCT_OFFSET_1A0_NEW,
            )
        )
    return patches


def _collect_cluster_patches(exe: bytes) -> list[PatchEntry]:
    seen: set[int] = set()
    patches: list[PatchEntry] = []
    for collector in (
        _collect_rsp_slot_patches,
        _collect_rbx8_patches,
        _collect_imul_stride_patches,
        _collect_add_reg_stride_patches,
        _collect_end_offset_patches,
        _collect_string_layer_1a0_patches,
    ):
        patches.extend(collector(exe, seen))
    patches.sort(key=lambda item: item[1])
    return patches


_EBM_LENGTH_PATCHES: list[PatchEntry] = [
    (
        "mov r9d, 400 -> 800",
        0x1401DDA51,
        bytes([0x41, 0xB9, 0x90, 0x01, 0x00, 0x00]),
        bytes([0x41, 0xB9, 0x20, 0x03, 0x00, 0x00]),
        EBM_BUF_MAX_VANILLA,
        EBM_BUF_MAX_PATCHED,
    ),
    (
        f"sub rsp, {_FRAME_VANILLA:#x} -> {_FRAME_PATCHED:#x}",
        0x1401DD9D6,
        bytes([0x48, 0x81, 0xEC, *_imm32_le(_FRAME_VANILLA)]),
        bytes([0x48, 0x81, 0xEC, *_imm32_le(_FRAME_PATCHED)]),
        _FRAME_VANILLA,
        _FRAME_PATCHED,
    ),
    (
        f"lea r11, [rsp+{_FRAME_VANILLA:#x}] -> [rsp+{_FRAME_PATCHED:#x}]",
        0x1401DDB6B,
        _imm32_le(_FRAME_VANILLA),
        _imm32_le(_FRAME_PATCHED),
        _FRAME_VANILLA,
        _FRAME_PATCHED,
    ),
]

# v7: explicit sites v6 collectors miss (add r15, lea/mov outside string layer, vector growth).
_GAP_PATCHES: list[PatchEntry] = [
    (
        "lea rcx,[r8+0x1c0] -> [r8+0x340] (vector growth)",
        0x1401DDA24,
        _imm32_le(_SLOT_OLD),
        _imm32_le(_SLOT_NEW),
        _SLOT_OLD,
        _SLOT_NEW,
    ),
    (
        "lea rcx,[rdx-0x1c0] -> [rdx-0x340] (vector shrink ptr)",
        0x1401DDA40,
        _imm32_signed(-_SLOT_OLD),
        _imm32_signed(-_SLOT_NEW),
        _SLOT_OLD,
        _SLOT_NEW,
    ),
    (
        "add r15,0x1c0 -> 0x340 (helper +0x1DD1D0 loop)",
        0x1401DD320,
        _imm32_le(_SLOT_OLD),
        _imm32_le(_SLOT_NEW),
        _SLOT_OLD,
        _SLOT_NEW,
    ),
    (
        "lea rdi,[rcx+0x1a0] -> [rcx+0x320] (helper +0x1DD0F0)",
        0x1401DD113,
        _imm32_le(_STRUCT_OFFSET_1A0_OLD),
        _imm32_le(_STRUCT_OFFSET_1A0_NEW),
        _STRUCT_OFFSET_1A0_OLD,
        _STRUCT_OFFSET_1A0_NEW,
    ),
    (
        "lea rax,[rdi-0x1a0] -> [rdi-0x320] (helper +0x1DD0F0 end)",
        0x1401DD19E,
        _imm32_signed(-_STRUCT_OFFSET_1A0_OLD),
        _imm32_signed(-_STRUCT_OFFSET_1A0_NEW),
        _STRUCT_OFFSET_1A0_OLD,
        _STRUCT_OFFSET_1A0_NEW,
    ),
    (
        "lea rdi,[r8+0x1a0] -> [r8+0x320] (helper +0x1DD1D0)",
        0x1401DD205,
        _imm32_le(_STRUCT_OFFSET_1A0_OLD),
        _imm32_le(_STRUCT_OFFSET_1A0_NEW),
        _STRUCT_OFFSET_1A0_OLD,
        _STRUCT_OFFSET_1A0_NEW,
    ),
    (
        "lea rsi,[rcx+0x1b0] -> [rcx+0x330] (helper +0x1DD1D0)",
        0x1401DD1F9,
        _imm32_le(_STRUCT_OFFSET_1B0_OLD),
        _imm32_le(_STRUCT_OFFSET_1B0_NEW),
        _STRUCT_OFFSET_1B0_OLD,
        _STRUCT_OFFSET_1B0_NEW,
    ),
    (
        "lea r8,[rsi-0x1b0] -> [rsi-0x330] (helper +0x1DD1D0)",
        0x1401DD223,
        _imm32_signed(-_STRUCT_OFFSET_1B0_OLD),
        _imm32_signed(-_STRUCT_OFFSET_1B0_NEW),
        _STRUCT_OFFSET_1B0_OLD,
        _STRUCT_OFFSET_1B0_NEW,
    ),
    (
        "lea rax,[rsi-0x1b0] -> [rsi-0x330] (helper +0x1DD1D0 loop end)",
        0x1401DD338,
        _imm32_signed(-_STRUCT_OFFSET_1B0_OLD),
        _imm32_signed(-_STRUCT_OFFSET_1B0_NEW),
        _STRUCT_OFFSET_1B0_OLD,
        _STRUCT_OFFSET_1B0_NEW,
    ),
    (
        "lea rcx,[rbx+0x1a0] -> [rbx+0x320] (copy loop +0x1DE020)",
        0x1401DE064,
        _imm32_le(_STRUCT_OFFSET_1A0_OLD),
        _imm32_le(_STRUCT_OFFSET_1A0_NEW),
        _STRUCT_OFFSET_1A0_OLD,
        _STRUCT_OFFSET_1A0_NEW,
    ),
    (
        "mov eax,[rdi+0x1b0] -> [rdi+0x330] (copy loop +0x1DE020)",
        0x1401DE06F,
        _imm32_le(_STRUCT_OFFSET_1B0_OLD),
        _imm32_le(_STRUCT_OFFSET_1B0_NEW),
        _STRUCT_OFFSET_1B0_OLD,
        _STRUCT_OFFSET_1B0_NEW,
    ),
    (
        "mov [rbx+0x1b8] -> [rbx+0x338] (copy loop +0x1DE020)",
        0x1401DE07C,
        _imm32_le(_STRUCT_OFFSET_1B8_OLD),
        _imm32_le(_STRUCT_OFFSET_1B8_NEW),
        _STRUCT_OFFSET_1B8_OLD,
        _STRUCT_OFFSET_1B8_NEW,
    ),
]


def apply_ebm_length_patch(exe: bytearray) -> list[dict]:
    vanilla = bytes(exe)
    all_patches = _EBM_LENGTH_PATCHES + _collect_cluster_patches(vanilla) + _GAP_PATCHES
    all_patches.sort(key=lambda item: item[1])
    applied: list[dict] = []

    for desc, va, old, new, limit_vanilla, limit_patched in all_patches:
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
