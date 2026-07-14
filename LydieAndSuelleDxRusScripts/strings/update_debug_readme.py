#!/usr/bin/env python3
"""Regenerate strings/debug/README.md translation status table from shard files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from strings_common import DEBUG_DIR, DEBUG_FILES_DIR, iter_shard_paths

STATUS_JSON = DEBUG_DIR / "translation_status.json"
README_PATH = DEBUG_DIR / "README.md"


def load_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"default": {"mt": True, "manual": False}}
    return json.loads(path.read_text(encoding="utf-8"))


def status_for(rel: str, status_doc: dict[str, Any]) -> tuple[bool, bool]:
    default = status_doc.get("default") or {}
    entry = status_doc.get(rel) or default
    mt = bool(entry.get("mt", default.get("mt", False)))
    manual = bool(entry.get("manual", default.get("manual", False)))
    return mt, manual


def mark(ok: bool) -> str:
    return "✓" if ok else "—"


def build_readme(files_dir: Path, status_doc: dict[str, Any]) -> str:
    rows: list[tuple[str, int, bool, bool]] = []
    for path in iter_shard_paths(files_dir):
        rel = path.relative_to(files_dir).as_posix()
        data = json.loads(path.read_text(encoding="utf-8"))
        n = len(data.get("entries") or {})
        mt, manual = status_for(rel, status_doc)
        rows.append((rel, n, mt, manual))

    total_files = len(rows)
    total_strings = sum(n for _, n, _, _ in rows)
    mt_done = sum(1 for _, _, mt, _ in rows if mt)
    manual_done = sum(1 for _, _, _, m in rows if m)

    lines = [
        "# Debug string shards",
        "",
        "Per-block / per-file translation shards live under [`files/`](files/).",
        "Edit shards directly, then rebuild the aggregate catalog with",
        "[`../assemble_debug_strings.py`](../assemble_debug_strings.py).",
        "",
        "Regenerate this table:",
        "",
        "```bash",
        "python3 strings/update_debug_readme.py",
        "```",
        "",
        f"**Summary:** {total_files} files, {total_strings} strings;",
        f"MT done: {mt_done}/{total_files}; manual edits: {manual_done}/{total_files}.",
        "",
        "Statuses are stored in [`translation_status.json`](translation_status.json)",
        "(`default` applies to files without an explicit entry).",
        "",
        "| Файл | Строк | MT перевод | Ручные правки |",
        "|------|------:|:----------:|:-------------:|",
    ]
    for rel, n, mt, manual in rows:
        lines.append(f"| `{rel}` | {n} | {mark(mt)} | {mark(manual)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files-dir", type=Path, default=DEBUG_FILES_DIR)
    parser.add_argument("--status", type=Path, default=STATUS_JSON)
    parser.add_argument("--readme", type=Path, default=README_PATH)
    args = parser.parse_args()

    files_dir = args.files_dir.resolve()
    if not files_dir.is_dir():
        raise SystemExit(f"Shards directory not found: {files_dir}")

    status_doc = load_status(args.status.resolve())
    text = build_readme(files_dir, status_doc)
    args.readme.parent.mkdir(parents=True, exist_ok=True)
    args.readme.write_text(text, encoding="utf-8")
    print(f"Wrote {args.readme}")


if __name__ == "__main__":
    main()
