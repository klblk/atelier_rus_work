#!/usr/bin/env python3
"""Assemble strings/debug/strings.json from per-block / per-file shards under files/."""

from __future__ import annotations

import argparse
from pathlib import Path

from backup_strings import backup_strings_json
from strings_common import (
    BACKUPS_DIR,
    DEBUG_FILES_DIR,
    PACK01_EBM_JSON_ROOT,
    PACK02_TEXT_EN_DIR,
    ROOT,
    STRINGS_JSON,
    build_catalog,
    catalog_stats,
    load_entries_from_shards,
    write_json_atomic,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files-dir", type=Path, default=DEBUG_FILES_DIR)
    parser.add_argument("--output", type=Path, default=STRINGS_JSON)
    parser.add_argument("--ebm-root", type=Path, default=PACK01_EBM_JSON_ROOT)
    parser.add_argument("--text-en-dir", type=Path, default=PACK02_TEXT_EN_DIR)
    parser.add_argument(
        "--backup-label",
        default="pre-assemble",
        help="Backup filename suffix for strings.json before write",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Keep only N most recent backups (0 = keep all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args()

    files_dir = args.files_dir.resolve()
    out_path = args.output.resolve()

    if not files_dir.is_dir():
        raise SystemExit(f"Shards directory not found: {files_dir}")

    entries = load_entries_from_shards(files_dir)
    if not entries:
        raise SystemExit(f"No shard entries found under {files_dir}")

    stats = catalog_stats(entries)
    print(
        f"Assembled {stats['total']} strings "
        f"(pack01_ebm={stats['pack01_ebm']}, pack02_text_en={stats['pack02_text_en']}, "
        f"translated={stats['translated']})"
    )

    if args.dry_run:
        print("Dry run — no file written")
        return

    if out_path.is_file():
        backup = backup_strings_json(
            out_path,
            BACKUPS_DIR,
            label=args.backup_label,
            keep=args.keep,
        )
        try:
            rel_backup = backup.relative_to(ROOT)
        except ValueError:
            rel_backup = backup
        print(f"Backup: {rel_backup}")

    catalog = build_catalog(
        entries,
        ebm_json_root=args.ebm_root.resolve(),
        text_en_dir=args.text_en_dir.resolve(),
    )
    write_json_atomic(out_path, catalog)
    try:
        rel_out = out_path.relative_to(ROOT)
    except ValueError:
        rel_out = out_path
    print(f"Wrote: {rel_out}")


if __name__ == "__main__":
    main()
