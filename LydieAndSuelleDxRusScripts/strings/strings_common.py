"""Shared helpers for LydieAndSuelleDxRusScripts translation catalog scripts."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CATALOG_VERSION = 1
CATALOG_REGRESSION_TOLERANCE = 5

LATIN_RE = re.compile(r"[A-Za-z]")
PACK02_STR_RE = re.compile(rb'<str Text="([^"]*)" String_No="(\d+)"')

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "LydieAndSuelleDxRusScripts"
BUILD_DIR = SCRIPTS_DIR / "build"
EXTRACTS_DIR = SCRIPTS_DIR / "extracts"

PACK02_TEXT_EN_DIR = EXTRACTS_DIR / "pack_extracts/PACK02_extract/saves/text_en"
PACK01_EBM_JSON_ROOT = EXTRACTS_DIR / "PACK01_event_ebm_extract/event/event_en"

DEBUG_DIR = SCRIPTS_DIR / "strings/debug"
STRINGS_JSON = DEBUG_DIR / "strings.json"
BACKUPS_DIR = DEBUG_DIR / "backups"

PROD_DIR = SCRIPTS_DIR / "strings/prod"
PROD_STRINGS_JSON = PROD_DIR / "strings.json"
PROD_BACKUPS_DIR = PROD_DIR / "backups"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_latin(text: str) -> bool:
    return bool(LATIN_RE.search(text))


def ebm_entry_id(rel_ebm_path: str, message_index: int) -> str:
    return f"ebm:{rel_ebm_path}:{message_index}"


def pack02_entry_id(string_no: str) -> str:
    return f"pack02:{string_no}"


def is_translated(entry: dict[str, Any]) -> bool:
    return bool((entry.get("translation") or "").strip())


def catalog_stats(entries: dict[str, dict[str, Any]]) -> dict[str, int]:
    pack01 = sum(1 for e in entries.values() if e.get("source") == "pack01_ebm")
    pack02 = sum(1 for e in entries.values() if e.get("source") == "pack02_text_en")
    translated = sum(1 for e in entries.values() if is_translated(e))
    return {
        "total": len(entries),
        "translated": translated,
        "pack01_ebm": pack01,
        "pack02_text_en": pack02,
    }


def write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON via temp file, verify round-trip, then atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        with tmp.open(encoding="utf-8") as f:
            json.load(f)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": CATALOG_VERSION, "entries": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def load_gust_json(path: Path) -> dict:
    """Load Gust tool JSON with hex literals and comments."""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(
        r"\b0x([0-9a-fA-F]+)\b",
        lambda m: str(int(m.group(1), 16)),
        text,
    )
    return json.loads(text)

