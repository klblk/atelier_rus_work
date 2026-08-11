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
PACK02_EXTRACT_DIR = EXTRACTS_DIR / "pack_extracts/PACK02_extract"
PACK01_EBM_JSON_ROOT = EXTRACTS_DIR / "PACK01_event_ebm_extract/event/event_en"

DEBUG_DIR = SCRIPTS_DIR / "strings/debug"
STRINGS_JSON = DEBUG_DIR / "strings.json"
BACKUPS_DIR = DEBUG_DIR / "backups"
DEBUG_FILES_DIR = DEBUG_DIR / "files"

PROD_DIR = SCRIPTS_DIR / "strings/prod"
PROD_STRINGS_JSON = PROD_DIR / "strings.json"
PROD_BACKUPS_DIR = PROD_DIR / "backups"

# str_event_chara_name.xml: String_No = 262145 + name_id
EVENT_CHARA_NAME_STRING_NO_BASE = 262145
NAME_ID_NONE = 0xFFFFFFFF
EVENT_CHARA_NAMES_XML = PACK02_TEXT_EN_DIR / "str_event_chara_name.xml"
SYSMESS_XML = PACK02_EXTRACT_DIR / "saves/systemmessage/sysmess.xml"

CHARA_NAME_STR_RE = re.compile(
    r'<str(?: Text="([^"]*)")? String_No="(\d+)"\s*/>',
)
SYSMESS_ATTR_RE = re.compile(r'<SysMess\s+([^/]+?)\s*/>')
SYSMESS_KV_RE = re.compile(r'(\w+)="([^"]*)"')


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


def ebm_block_from_path(rel_ebm: str) -> str:
    parts = rel_ebm.split("/")
    return parts[0] if parts else rel_ebm


def load_name_id_speakers(chara_names_xml: Path) -> dict[int, str]:
    text = chara_names_xml.read_text(encoding="utf-8")
    speakers: dict[int, str] = {}
    for match in CHARA_NAME_STR_RE.finditer(text):
        name = match.group(1) or ""
        string_no = int(match.group(2))
        name_id = string_no - EVENT_CHARA_NAME_STRING_NO_BASE
        if name_id < 0:
            continue
        speakers[name_id] = name
    if not speakers:
        raise SystemExit(f"No character names parsed from {chara_names_xml}")
    return speakers


def normalize_name_id(name_id: object) -> int | None:
    if name_id is None:
        return None
    if isinstance(name_id, str):
        name_id = int(name_id, 16) if name_id.startswith("0x") else int(name_id)
    value = int(name_id)
    if value == NAME_ID_NONE or value == -1:
        return NAME_ID_NONE
    return value


def speaker_name(name_id: int | None, speakers: dict[int, str]) -> str:
    if name_id is None:
        return "Unknown"
    if name_id == NAME_ID_NONE:
        return "(no speaker)"
    return speakers.get(name_id, f"unknown(name_id={name_id})")


def chara_tag_to_speaker(tag: str) -> str | None:
    """Map sysmess CharaTag to ebm-style EN speaker name; None if no speaker."""
    if not tag or tag == "CHARA_NONE" or tag.startswith("CHARA_NPC"):
        return None
    if not tag.startswith("CHARA_"):
        return None
    rest = tag[len("CHARA_") :]
    if rest.endswith("_B"):
        rest = rest[:-2]
    if not rest:
        return None
    return "_".join(part.capitalize() for part in rest.split("_"))


def load_sysmess_speakers(sysmess_xml: Path) -> dict[str, str]:
    """STRING_ID -> display speaker name from sysmess.xml (skips NONE/NPC)."""
    text = sysmess_xml.read_text(encoding="utf-8", errors="replace")
    speakers: dict[str, str] = {}
    for attrs in SYSMESS_ATTR_RE.findall(text):
        kv = dict(SYSMESS_KV_RE.findall(attrs))
        string_id = kv.get("STRING_ID")
        if not string_id:
            continue
        name = chara_tag_to_speaker(kv.get("CharaTag", ""))
        if name is None:
            continue
        speakers[string_id] = name
    return speakers


def iter_shard_paths(files_dir: Path) -> list[Path]:
    if not files_dir.is_dir():
        return []
    return sorted(p for p in files_dir.rglob("*.json") if p.is_file())


def load_entries_from_shards(files_dir: Path) -> dict[str, dict[str, Any]]:
    """Merge all shard JSON entries; raise on duplicate entry ids."""
    merged: dict[str, dict[str, Any]] = {}
    for path in iter_shard_paths(files_dir):
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry_id, entry in data.get("entries", {}).items():
            if entry_id in merged:
                raise SystemExit(f"Duplicate entry id {entry_id!r} in {path}")
            merged[entry_id] = entry
    return merged


def build_catalog(
    entries: dict[str, dict[str, Any]],
    *,
    ebm_json_root: Path,
    text_en_dir: Path,
    merge_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stats = catalog_stats(entries)
    if merge_stats:
        stats.update(merge_stats)
    try:
        pack01_src = str(ebm_json_root.relative_to(ROOT))
    except ValueError:
        pack01_src = str(ebm_json_root)
    try:
        pack02_src = str(text_en_dir.relative_to(ROOT))
    except ValueError:
        pack02_src = str(text_en_dir)
    return {
        "version": CATALOG_VERSION,
        "generated_at": utc_now_iso(),
        "sources": {
            "pack01_ebm": pack01_src,
            "pack02_text_en": pack02_src,
        },
        "stats": stats,
        "entries": entries,
    }

