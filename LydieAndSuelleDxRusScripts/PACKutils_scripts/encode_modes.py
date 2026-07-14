"""Encoding mode helpers for PACK01/PACK02 string apply scripts."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum


class EncodeMode(str, Enum):
    TRANSLATED = "translated"
    FULL = "full"
    NONE = "none"


def resolve_output_text(
    original: str,
    translation: str,
    mode: EncodeMode,
    encode_fn: Callable[[str], str] | None,
) -> str | None:
    """Return text to write, or None if the catalog entry should be skipped."""
    has_translation = bool((translation or "").strip())

    if mode == EncodeMode.TRANSLATED:
        if not has_translation:
            return None
        text = translation.strip()
    elif mode == EncodeMode.NONE:
        if not has_translation:
            return None
        return translation.strip()
    else:
        text = translation.strip() if has_translation else original

    if encode_fn is None:
        return text
    return encode_fn(text)
