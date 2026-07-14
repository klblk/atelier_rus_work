"""Phys-glyph text encoder wrapper for PACK apply scripts."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from encode_modes import EncodeMode

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PHYS_GLYPH_DIR = SCRIPTS_DIR / "exe_patches/phys_glyph"
if str(PHYS_GLYPH_DIR) not in sys.path:
    sys.path.insert(0, str(PHYS_GLYPH_DIR))

from encode_text import encode_text, load_encode_map  # noqa: E402


def utf8_byte_length(text: str) -> int:
    return len(text.encode("utf-8"))


def make_encode_fn(resolved_path: Path, mode: EncodeMode) -> Callable[[str], str] | None:
    if mode == EncodeMode.NONE:
        return None
    if not resolved_path.is_file():
        raise FileNotFoundError(f"resolved carrier map not found: {resolved_path}")
    letter_carrier = load_encode_map(resolved_path)
    return lambda text: encode_text(text, letter_carrier)
