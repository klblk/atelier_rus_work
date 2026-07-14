#!/usr/bin/env python3
"""Sync translations from debug strings.json into prod strings.json."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from backup_strings import backup_strings_json
from strings_common import (
    PROD_BACKUPS_DIR,
    PROD_STRINGS_JSON,
    ROOT,
    STRINGS_JSON,
    catalog_stats,
    is_translated,
    load_catalog,
    utc_now_iso,
    write_json_atomic,
)

SyncMode = Literal["update", "full", "skip-existing"]


@dataclass
class SyncReport:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    mismatched: int = 0
    mismatched_ids: list[str] | None = None

    def __post_init__(self) -> None:
        if self.mismatched_ids is None:
            self.mismatched_ids = []


def sync_entries(
    debug_entries: dict[str, dict[str, Any]],
    prod_entries: dict[str, dict[str, Any]],
    mode: SyncMode,
) -> SyncReport:
    report = SyncReport()

    for entry_id, debug_entry in debug_entries.items():
        prod_entry = prod_entries.get(entry_id)

        if prod_entry is None:
            if is_translated(debug_entry):
                prod_entries[entry_id] = dict(debug_entry)
                report.added += 1
            else:
                report.skipped += 1
            continue

        if prod_entry.get("original") != debug_entry.get("original"):
            report.mismatched += 1
            report.mismatched_ids.append(entry_id)
            report.skipped += 1
            continue

        debug_tr = debug_entry.get("translation") or ""
        prod_tr = prod_entry.get("translation") or ""

        if mode == "update":
            if not is_translated(debug_entry):
                report.skipped += 1
                continue
            if debug_tr == prod_tr:
                report.skipped += 1
                continue
            prod_entry["translation"] = debug_tr
            report.updated += 1
            continue

        if mode == "full":
            if debug_tr == prod_tr:
                report.skipped += 1
                continue
            prod_entry["translation"] = debug_tr
            report.updated += 1
            continue

        # skip-existing
        if is_translated(prod_entry):
            report.skipped += 1
            continue
        if debug_tr == prod_tr:
            report.skipped += 1
            continue
        prod_entry["translation"] = debug_tr
        report.updated += 1

    return report


def build_prod_catalog(
    prod_catalog: dict[str, Any],
    prod_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "version": prod_catalog.get("version"),
        "generated_at": utc_now_iso(),
        "sources": prod_catalog.get("sources", {}),
        "stats": catalog_stats(prod_entries),
        "entries": prod_entries,
    }


def print_report(mode: SyncMode, report: SyncReport) -> None:
    print(f"Mode: {mode}")
    print(
        f"Added: {report.added} | Updated: {report.updated} | "
        f"Skipped: {report.skipped} | Mismatched originals: {report.mismatched}"
    )
    if report.mismatched_ids:
        shown = report.mismatched_ids[:10]
        for entry_id in shown:
            print(f"  mismatch: {entry_id}")
        if len(report.mismatched_ids) > len(shown):
            print(f"  ... and {len(report.mismatched_ids) - len(shown)} more")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("update", "full", "skip-existing"),
        default="update",
        help="update: copy non-empty debug translations (default); "
        "full: always copy including empty; "
        "skip-existing: skip prod entries that already have a translation",
    )
    parser.add_argument("--source", type=Path, default=STRINGS_JSON, help="debug strings.json")
    parser.add_argument("--dest", type=Path, default=PROD_STRINGS_JSON, help="prod strings.json")
    parser.add_argument(
        "--backup-label",
        default="pre-sync-debug",
        help="Backup filename suffix for prod before write",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Keep only N most recent prod backups (0 = keep all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args()

    source = args.source.resolve()
    dest = args.dest.resolve()

    if not source.is_file():
        raise SystemExit(f"Source not found: {source}")
    if not dest.is_file():
        raise SystemExit(f"Dest not found: {dest}")

    debug_catalog = load_catalog(source)
    prod_catalog = load_catalog(dest)
    debug_entries = debug_catalog.get("entries", {})
    prod_entries = dict(prod_catalog.get("entries", {}))

    report = sync_entries(debug_entries, prod_entries, args.mode)
    print_report(args.mode, report)

    if args.dry_run:
        print("Dry run — no file written")
        return

    backup = backup_strings_json(dest, PROD_BACKUPS_DIR, label=args.backup_label, keep=args.keep)
    try:
        rel_backup = backup.relative_to(ROOT)
    except ValueError:
        rel_backup = backup
    print(f"Backup: {rel_backup}")

    catalog = build_prod_catalog(prod_catalog, prod_entries)
    write_json_atomic(dest, catalog)
    try:
        rel_dest = dest.relative_to(ROOT)
    except ValueError:
        rel_dest = dest
    print(f"Wrote: {rel_dest}")


if __name__ == "__main__":
    main()
