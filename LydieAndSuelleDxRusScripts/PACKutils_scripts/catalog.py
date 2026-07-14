"""Load and group strings.json catalog entries for PACK apply scripts."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"expected entries object in {path}")
    return entries


def group_pack01_entries(entries: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries.values():
        if entry.get("source") != "pack01_ebm":
            continue
        grouped[entry["path"]].append(entry)
    for path in grouped:
        grouped[path].sort(key=lambda item: item["index"])
    return grouped


def group_pack02_entries(entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in entries.values()
        if entry.get("source") == "pack02_text_en"
    ]
