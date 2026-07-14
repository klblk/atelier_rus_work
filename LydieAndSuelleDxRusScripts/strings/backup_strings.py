#!/usr/bin/env python3
"""Backup strings.json translation catalogs (debug, prod, or custom paths)."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from strings_common import (
    BACKUPS_DIR,
    PROD_BACKUPS_DIR,
    PROD_STRINGS_JSON,
    ROOT,
    STRINGS_JSON,
)

CATALOG_TARGETS: dict[str, tuple[Path, Path]] = {
    "debug": (STRINGS_JSON, BACKUPS_DIR),
    "prod": (PROD_STRINGS_JSON, PROD_BACKUPS_DIR),
}


def prune_backups(backup_dir: Path, keep: int) -> list[Path]:
    backups = sorted(
        backup_dir.glob("strings_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed: list[Path] = []
    for old in backups[keep:]:
        old.unlink()
        removed.append(old)
    return removed


def backup_strings_json(
    source: Path,
    backup_dir: Path,
    *,
    label: str | None,
    keep: int,
) -> Path:
    if not source.is_file():
        raise SystemExit(f"Source not found: {source}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if label:
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        dest = backup_dir / f"strings_{stamp}_{safe_label}.json"
    else:
        dest = backup_dir / f"strings_{stamp}.json"

    shutil.copy2(source, dest)
    if keep > 0:
        prune_backups(backup_dir, keep)
    return dest


def resolve_paths(
    *,
    target: str | None,
    source: Path | None,
    backup_dir: Path | None,
) -> tuple[Path, Path]:
    if target is not None:
        if source is not None or backup_dir is not None:
            raise SystemExit("--target is mutually exclusive with --source/--backup-dir")
        try:
            src, bdir = CATALOG_TARGETS[target]
        except KeyError:
            raise SystemExit(f"Unknown --target {target!r}; use: {', '.join(CATALOG_TARGETS)}")
        return src.resolve(), bdir.resolve()

    if source is None or backup_dir is None:
        raise SystemExit("Specify --target debug|prod or both --source and --backup-dir")
    return source.resolve(), backup_dir.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=sorted(CATALOG_TARGETS),
        help="Preset catalog: debug or prod strings.json + backups/",
    )
    parser.add_argument("--source", type=Path, help="strings.json to back up")
    parser.add_argument("--backup-dir", type=Path, help="Directory for strings_*.json backups")
    parser.add_argument("--label", help="Optional backup filename suffix")
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Keep only N most recent backups (0 = keep all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved paths without copying",
    )
    args = parser.parse_args()

    source, backup_dir = resolve_paths(
        target=args.target,
        source=args.source,
        backup_dir=args.backup_dir,
    )

    if args.dry_run:
        print(f"source: {source}")
        print(f"backup_dir: {backup_dir}")
        return

    dest = backup_strings_json(source, backup_dir, label=args.label, keep=args.keep)
    try:
        rel = dest.relative_to(ROOT)
    except ValueError:
        rel = dest
    print(f"Backup: {rel}")


if __name__ == "__main__":
    main()
