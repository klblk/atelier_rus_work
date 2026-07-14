"""Shared paths for phys_glyph exe patch scripts."""

from __future__ import annotations

import sys
from pathlib import Path

PHYS_GLYPH_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PHYS_GLYPH_DIR.parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    ATLAS_TABLE_CSV,
    PATCHED_EXE,
    PHYS_GLYPH_JSON_DIR,
    ROOT,
    STEAMLESS_DEST_EXE,
)

JSON_DIR = PHYS_GLYPH_JSON_DIR
PHYS_BLOCK_MAP_JSON = JSON_DIR / "phys_block_map.json"
PHYS_BLOCK_MAP_MD = JSON_DIR / "phys_block_map.md"
VIRTUAL_JSON = JSON_DIR / "virtual_phys_blocks.json"
LETTER_CARRIER_MAP_JSON = JSON_DIR / "letter_carrier_map.json"
LETTER_CARRIER_MAP_BACKUP_JSON = JSON_DIR / "letter_carrier_map.json.bak"
LETTER_CARRIER_MAP_RESOLVED_JSON = JSON_DIR / "letter_carrier_map_resolved.json"
ATLAS_TABLE = ATLAS_TABLE_CSV

SCAN_SCRIPT = PHYS_GLYPH_DIR / "scan_phys_block_map.py"
BUILD_VIRTUAL_SCRIPT = PHYS_GLYPH_DIR / "build_virtual_phys_blocks.py"
BUILD_CARRIER_SCRIPT = PHYS_GLYPH_DIR / "build_letter_carrier_map.py"

DEFAULT_EXE_IN = STEAMLESS_DEST_EXE
DEFAULT_EXE_OUT = PATCHED_EXE
