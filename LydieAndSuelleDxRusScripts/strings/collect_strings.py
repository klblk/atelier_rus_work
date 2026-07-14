#!/usr/bin/env python3
"""Collect English strings for translation into strings/debug/strings.json.

Sources:
- PACK01 EBM JSON (event/event_en/*.json) extracted via PACK01scripts/extract_pack01_event_ebm.py
- PACK02 text_en str_*.xml

Only entries containing Latin letters [A-Za-z] are collected.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from backup_strings import backup_strings_json
from strings_common import (
    BACKUPS_DIR,
    CATALOG_REGRESSION_TOLERANCE,
    CATALOG_VERSION,
    PACK01_EBM_JSON_ROOT,
    PACK02_STR_RE,
    PACK02_TEXT_EN_DIR,
    ROOT,
    STRINGS_JSON,
    catalog_stats,
    ebm_entry_id,
    has_latin,
    is_translated,
    load_gust_json,
    pack02_entry_id,
    utc_now_iso,
)


def collect_pack01_ebm_strings(ebm_json_root: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for json_path in sorted(ebm_json_root.rglob("*.json")):
        rel_ebm = json_path.relative_to(ebm_json_root).with_suffix(".ebm").as_posix()
        data = load_gust_json(json_path)
        for index, message in enumerate(data.get("messages", [])):
            original = message.get("msg_string", "")
            if not original or not has_latin(original):
                continue
            entry_id = ebm_entry_id(rel_ebm, index)
            entries[entry_id] = {
                "source": "pack01_ebm",
                "path": rel_ebm,
                "index": index,
                "original": original,
                "translation": "",
            }
    return entries


def collect_pack02_strings(text_en_dir: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for xml_path in sorted(text_en_dir.glob("str_*.xml")):
        if xml_path.name == "strcombineall.xml":
            continue
        data = xml_path.read_bytes()
        for match in PACK02_STR_RE.finditer(data):
            original = match.group(1).decode("utf-8", errors="replace")
            if not has_latin(original):
                continue
            string_no = match.group(2).decode("ascii")
            entry_id = pack02_entry_id(string_no)
            entries[entry_id] = {
                "source": "pack02_text_en",
                "file": xml_path.name,
                "string_no": string_no,
                "original": original,
                "translation": "",
            }
    return entries


def collect_all_strings(*, ebm_json_root: Path, text_en_dir: Path) -> dict[str, dict[str, Any]]:
    entries = collect_pack01_ebm_strings(ebm_json_root)
    entries.update(collect_pack02_strings(text_en_dir))
    return entries


def merge_entries(
    existing: dict[str, dict[str, Any]],
    collected: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    merged: dict[str, dict[str, Any]] = {}
    changed: list[str] = []
    for entry_id, entry in collected.items():
        new_entry = dict(entry)
        old = existing.get(entry_id)
        if old is not None and old.get("original") == entry.get("original"):
            new_entry["translation"] = old.get("translation", "")
        elif old is not None:
            changed.append(entry_id)
            new_entry["translation"] = ""
        merged[entry_id] = new_entry
    return merged, changed


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": CATALOG_VERSION, "entries": {}}
    return json.loads(path.read_text(encoding="utf-8"))


class CatalogRegressionError(RuntimeError):
    pass


def translation_loss_report(
    old_entries: dict[str, dict[str, Any]],
    new_entries: dict[str, dict[str, Any]],
) -> tuple[int, dict[str, int]]:
    from collections import Counter

    lost_by_file: Counter[str] = Counter()
    lost = 0
    for entry_id, old in old_entries.items():
        old_tr = (old.get("translation") or "").strip()
        if not old_tr:
            continue
        new = new_entries.get(entry_id)
        new_tr = (new.get("translation") or "").strip() if new else ""
        if not new_tr:
            lost += 1
            lost_by_file[old.get("file") or old.get("path") or "?"] += 1
    return lost, dict(lost_by_file.most_common(10))


def save_catalog(
    entries: dict[str, dict[str, Any]],
    path: Path,
    *,
    ebm_json_root: Path,
    text_en_dir: Path,
    merge_stats: dict[str, Any] | None,
    force: bool,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file() and not force:
        old_entries = load_catalog(path).get("entries", {})
        old_translated = catalog_stats(old_entries)["translated"]
        new_translated = catalog_stats(entries)["translated"]
        if new_translated < old_translated - CATALOG_REGRESSION_TOLERANCE:
            lost, top_files = translation_loss_report(old_entries, entries)
            top = ", ".join(f"{f}: {n}" for f, n in top_files.items())
            raise CatalogRegressionError(
                f"Refusing to save {path}: translated {old_translated} -> {new_translated} "
                f"(lost {lost} non-empty translations). Top files: {top}. Use --force to override."
            )

    stats = catalog_stats(entries)
    if merge_stats:
        stats.update(merge_stats)

    catalog = {
        "version": CATALOG_VERSION,
        "generated_at": utc_now_iso(),
        "sources": {
            "pack01_ebm": str(ebm_json_root.relative_to(ROOT)),
            "pack02_text_en": str(text_en_dir.relative_to(ROOT)),
        },
        "stats": stats,
        "entries": entries,
    }
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ebm-root", type=Path, default=PACK01_EBM_JSON_ROOT)
    parser.add_argument("--text-en-dir", type=Path, default=PACK02_TEXT_EN_DIR)
    parser.add_argument("--output", type=Path, default=STRINGS_JSON)
    parser.add_argument("--merge", action="store_true", help="Rebuild and preserve translations where original matches")
    parser.add_argument("--force", action="store_true", help="Rebuild even if regression check would fail")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, do not write output")
    parser.add_argument("--backup-label", help="Optional backup filename suffix")
    parser.add_argument("--keep", type=int, default=10, help="Keep only N most recent backups (0 = keep all)")
    args = parser.parse_args()

    ebm_root = args.ebm_root.resolve()
    text_en_dir = args.text_en_dir.resolve()
    out_path = args.output.resolve()

    if out_path.is_file() and not args.merge and not args.force:
        print(f"Skip (exists): {out_path}")
        return

    if not ebm_root.is_dir():
        raise SystemExit(f"EBM JSON root not found: {ebm_root}")
    if not text_en_dir.is_dir():
        raise SystemExit(f"PACK02 text_en not found: {text_en_dir}")

    collected = collect_all_strings(ebm_json_root=ebm_root, text_en_dir=text_en_dir)
    stats = catalog_stats(collected)
    merge_meta: dict[str, Any] = {}

    if args.merge and out_path.is_file():
        existing = load_catalog(out_path).get("entries", {})
        collected, changed = merge_entries(existing, collected)
        stats = catalog_stats(collected)
        merge_meta["merged"] = len(existing)
        merge_meta["changed_originals"] = len(changed)
        if changed:
            print(f"Reset translation for {len(changed)} entries with changed original")

    print(
        f"Collected {stats['total']} strings "
        f"(pack01_ebm={stats['pack01_ebm']}, pack02_text_en={stats['pack02_text_en']}, "
        f"translated={stats['translated']})"
    )

    if args.dry_run:
        print("Dry run — no file written")
        return

    if (args.merge or args.force) and out_path.is_file():
        backup = backup_strings_json(out_path, BACKUPS_DIR, label=args.backup_label, keep=args.keep)
        print(f"Backup: {backup.relative_to(ROOT)}")

    saved = save_catalog(
        collected,
        out_path,
        ebm_json_root=ebm_root,
        text_en_dir=text_en_dir,
        merge_stats=merge_meta or None,
        force=args.force,
    )
    print(f"Wrote {saved.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

