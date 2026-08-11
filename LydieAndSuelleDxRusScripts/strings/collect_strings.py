#!/usr/bin/env python3
"""Collect English strings into per-block/per-file shards and strings/debug/strings.json.

Sources:
- PACK01 EBM JSON (event/event_en/*.json) — shards under files/ebm/{block}.json
- PACK02 text_en str_*.xml — shards under files/pack02/{stem}.json

Only entries containing Latin letters [A-Za-z] are collected.
EBM entries include a speaker field resolved from str_event_chara_name.xml.
str_system_message entries include a speaker field resolved from sysmess.xml.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from backup_strings import backup_strings_json
from strings_common import (
    BACKUPS_DIR,
    CATALOG_REGRESSION_TOLERANCE,
    DEBUG_FILES_DIR,
    EVENT_CHARA_NAMES_XML,
    PACK01_EBM_JSON_ROOT,
    PACK02_STR_RE,
    PACK02_TEXT_EN_DIR,
    ROOT,
    STRINGS_JSON,
    SYSMESS_XML,
    build_catalog,
    catalog_stats,
    ebm_block_from_path,
    ebm_entry_id,
    has_latin,
    iter_shard_paths,
    load_catalog,
    load_entries_from_shards,
    load_gust_json,
    load_name_id_speakers,
    load_sysmess_speakers,
    normalize_name_id,
    pack02_entry_id,
    speaker_name,
    utc_now_iso,
    write_json_atomic,
)


class CatalogRegressionError(RuntimeError):
    pass


def collect_pack01_ebm_strings(
    ebm_json_root: Path,
    speakers: dict[int, str],
) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for json_path in sorted(ebm_json_root.rglob("*.json")):
        rel_ebm = json_path.relative_to(ebm_json_root).with_suffix(".ebm").as_posix()
        data = load_gust_json(json_path)
        for index, message in enumerate(data.get("messages", [])):
            original = message.get("msg_string", "")
            if not original or not has_latin(original):
                continue
            entry_id = ebm_entry_id(rel_ebm, index)
            name_id = normalize_name_id(message.get("name_id"))
            entries[entry_id] = {
                "source": "pack01_ebm",
                "path": rel_ebm,
                "index": index,
                "speaker": speaker_name(name_id, speakers),
                "original": original,
                "translation": "",
            }
    return entries


def collect_pack02_strings(
    text_en_dir: Path,
    sysmess_speakers: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    sysmess_speakers = sysmess_speakers or {}
    for xml_path in sorted(text_en_dir.glob("str_*.xml")):
        if xml_path.name == "strcombineall.xml":
            continue
        is_system_message = xml_path.name == "str_system_message.xml"
        data = xml_path.read_bytes()
        for match in PACK02_STR_RE.finditer(data):
            original = match.group(1).decode("utf-8", errors="replace")
            if not has_latin(original):
                continue
            string_no = match.group(2).decode("ascii")
            entry_id = pack02_entry_id(string_no)
            entry: dict[str, Any] = {
                "source": "pack02_text_en",
                "file": xml_path.name,
                "string_no": string_no,
                "original": original,
                "translation": "",
            }
            if is_system_message:
                speaker = sysmess_speakers.get(string_no)
                if speaker:
                    entry["speaker"] = speaker
            entries[entry_id] = entry
    return entries


def collect_all_strings(
    *,
    ebm_json_root: Path,
    text_en_dir: Path,
    speakers: dict[int, str],
    sysmess_speakers: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    entries = collect_pack01_ebm_strings(ebm_json_root, speakers)
    entries.update(collect_pack02_strings(text_en_dir, sysmess_speakers))
    return entries


def import_translations(
    collected: dict[str, dict[str, Any]],
    source_entries: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Copy translation when entry id exists and original matches."""
    imported = 0
    out: dict[str, dict[str, Any]] = {}
    for entry_id, entry in collected.items():
        new_entry = dict(entry)
        old = source_entries.get(entry_id)
        if old is not None and old.get("original") == entry.get("original"):
            tr = old.get("translation", "")
            if tr != new_entry.get("translation", ""):
                imported += 1
            new_entry["translation"] = tr
        out[entry_id] = new_entry
    return out, imported


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


def check_regression(
    old_entries: dict[str, dict[str, Any]],
    new_entries: dict[str, dict[str, Any]],
    *,
    force: bool,
) -> None:
    if force or not old_entries:
        return
    old_translated = catalog_stats(old_entries)["translated"]
    new_translated = catalog_stats(new_entries)["translated"]
    if new_translated < old_translated - CATALOG_REGRESSION_TOLERANCE:
        lost, top_files = translation_loss_report(old_entries, new_entries)
        top = ", ".join(f"{f}: {n}" for f, n in top_files.items())
        raise CatalogRegressionError(
            f"Refusing to save catalog: translated {old_translated} -> {new_translated} "
            f"(lost {lost} non-empty translations). Top files: {top}. Use --force to override."
        )


def write_shards(entries: dict[str, dict[str, Any]], files_dir: Path) -> tuple[int, int]:
    """Write EBM block shards and pack02 per-xml shards. Returns (ebm_shards, pack02_shards)."""
    ebm_by_block: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    pack02_by_file: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for entry_id, entry in entries.items():
        source = entry.get("source")
        if source == "pack01_ebm":
            block = ebm_block_from_path(entry.get("path") or "")
            ebm_by_block[block][entry_id] = entry
        elif source == "pack02_text_en":
            file_name = entry.get("file") or "unknown.xml"
            pack02_by_file[file_name][entry_id] = entry

    stamp = utc_now_iso()
    ebm_dir = files_dir / "ebm"
    pack02_dir = files_dir / "pack02"
    ebm_dir.mkdir(parents=True, exist_ok=True)
    pack02_dir.mkdir(parents=True, exist_ok=True)

    for block, block_entries in sorted(ebm_by_block.items()):
        write_json_atomic(
            ebm_dir / f"{block}.json",
            {
                "version": 1,
                "source": "pack01_ebm",
                "block": block,
                "generated_at": stamp,
                "entries": block_entries,
            },
        )

    for file_name, file_entries in sorted(pack02_by_file.items()):
        stem = Path(file_name).stem
        write_json_atomic(
            pack02_dir / f"{stem}.json",
            {
                "version": 1,
                "source": "pack02_text_en",
                "file": file_name,
                "generated_at": stamp,
                "entries": file_entries,
            },
        )

    return len(ebm_by_block), len(pack02_by_file)


def shards_exist(files_dir: Path) -> bool:
    return bool(iter_shard_paths(files_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ebm-root", type=Path, default=PACK01_EBM_JSON_ROOT)
    parser.add_argument("--text-en-dir", type=Path, default=PACK02_TEXT_EN_DIR)
    parser.add_argument("--output", type=Path, default=STRINGS_JSON)
    parser.add_argument("--files-dir", type=Path, default=DEBUG_FILES_DIR)
    parser.add_argument(
        "--chara-names-xml",
        type=Path,
        default=EVENT_CHARA_NAMES_XML,
        help="PACK02 str_event_chara_name.xml for EBM speaker names",
    )
    parser.add_argument(
        "--sysmess-xml",
        type=Path,
        default=SYSMESS_XML,
        help="PACK02 sysmess.xml for str_system_message speaker names",
    )
    parser.add_argument("--merge", action="store_true", help="Rebuild and preserve translations where original matches")
    parser.add_argument("--force", action="store_true", help="Rebuild even if regression check would fail")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, do not write output")
    parser.add_argument(
        "--import-translations",
        nargs="?",
        const=STRINGS_JSON,
        default=None,
        type=Path,
        help="Seed translations from a catalog (default path: strings/debug/strings.json)",
    )
    parser.add_argument("--backup-label", help="Optional backup filename suffix")
    parser.add_argument("--keep", type=int, default=10, help="Keep only N most recent backups (0 = keep all)")
    args = parser.parse_args()

    ebm_root = args.ebm_root.resolve()
    text_en_dir = args.text_en_dir.resolve()
    out_path = args.output.resolve()
    files_dir = args.files_dir.resolve()
    chara_xml = args.chara_names_xml.resolve()
    sysmess_xml = args.sysmess_xml.resolve()

    if (out_path.is_file() or shards_exist(files_dir)) and not args.merge and not args.force:
        print(f"Skip (exists): catalog or shards under {files_dir}")
        return

    if not ebm_root.is_dir():
        raise SystemExit(f"EBM JSON root not found: {ebm_root}")
    if not text_en_dir.is_dir():
        raise SystemExit(f"PACK02 text_en not found: {text_en_dir}")
    if not chara_xml.is_file():
        raise SystemExit(f"Character names XML not found: {chara_xml}")
    if not sysmess_xml.is_file():
        raise SystemExit(f"sysmess.xml not found: {sysmess_xml}")

    speakers = load_name_id_speakers(chara_xml)
    sysmess_speakers = load_sysmess_speakers(sysmess_xml)
    collected = collect_all_strings(
        ebm_json_root=ebm_root,
        text_en_dir=text_en_dir,
        speakers=speakers,
        sysmess_speakers=sysmess_speakers,
    )
    merge_meta: dict[str, Any] = {}

    if args.import_translations is not None:
        import_path = args.import_translations.resolve()
        if not import_path.is_file():
            raise SystemExit(f"Import catalog not found: {import_path}")
        imported_src = load_catalog(import_path).get("entries", {})
        collected, n_imported = import_translations(collected, imported_src)
        merge_meta["imported_translations"] = n_imported
        print(f"Imported translations from {import_path}: {n_imported} applied")

    existing: dict[str, dict[str, Any]] = {}
    if args.merge:
        if shards_exist(files_dir):
            existing = load_entries_from_shards(files_dir)
        elif out_path.is_file():
            existing = load_catalog(out_path).get("entries", {})
        if existing:
            collected, changed = merge_entries(existing, collected)
            merge_meta["merged"] = len(existing)
            merge_meta["changed_originals"] = len(changed)
            if changed:
                print(f"Reset translation for {len(changed)} entries with changed original")

    old_for_regression: dict[str, dict[str, Any]] = {}
    if out_path.is_file():
        old_for_regression = load_catalog(out_path).get("entries", {})
    elif shards_exist(files_dir):
        old_for_regression = load_entries_from_shards(files_dir)

    check_regression(old_for_regression, collected, force=args.force)

    stats = catalog_stats(collected)
    print(
        f"Collected {stats['total']} strings "
        f"(pack01_ebm={stats['pack01_ebm']}, pack02_text_en={stats['pack02_text_en']}, "
        f"translated={stats['translated']})"
    )

    if args.dry_run:
        print("Dry run — no file written")
        return

    if out_path.is_file() and (args.merge or args.force):
        backup = backup_strings_json(out_path, BACKUPS_DIR, label=args.backup_label, keep=args.keep)
        print(f"Backup: {backup.relative_to(ROOT)}")

    n_ebm, n_pack02 = write_shards(collected, files_dir)
    print(f"Wrote shards: ebm blocks={n_ebm}, pack02 files={n_pack02} under {files_dir.relative_to(ROOT)}")

    catalog = build_catalog(
        collected,
        ebm_json_root=ebm_root,
        text_en_dir=text_en_dir,
        merge_stats=merge_meta or None,
    )
    write_json_atomic(out_path, catalog)
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
