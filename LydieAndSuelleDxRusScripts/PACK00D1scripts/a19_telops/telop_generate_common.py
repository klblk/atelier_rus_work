"""Shared paths and helpers for a19_telop PNG generation."""

from __future__ import annotations

import sys
from pathlib import Path

A19_TELOPS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = A19_TELOPS_DIR.parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import BUILD_DIR, ROOT  # noqa: E402

DEFAULT_GRADIENTS_JSON = A19_TELOPS_DIR / "gradients.json"
DEFAULT_SPRITES_JSON = A19_TELOPS_DIR / "sprites.json"
DEFAULT_FONT = ROOT / "fonts/MarckScript-Regular.ttf"
BUILD_A19_TELOPS_DIR = BUILD_DIR / "a19_telops"
GRADIENTS_OUT_DIR = BUILD_A19_TELOPS_DIR / "gradients"
SPRITES_OUT_DIR = BUILD_A19_TELOPS_DIR / "sprites"


def gradient_tile_height(gradient_id: str) -> int:
    if gradient_id == "gradient12":
        return 192
    return 96


def default_pointsize(sprite_height: int) -> int:
    return 96 if sprite_height == 192 else 48


def escape_im_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("@", "\\@")
        .replace("%", "\\%")
    )
