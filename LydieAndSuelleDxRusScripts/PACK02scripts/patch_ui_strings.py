#!/usr/bin/env python3
"""Patch ui_en XML: add string_id from ui_strings.json; write sparse tree to PACK02_patch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PACK02_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACK02_DIR.parent
STRINGS_DIR = SCRIPTS_DIR / "strings"
for path in (SCRIPTS_DIR, STRINGS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rus_scripts_common import (  # noqa: E402
    PACK02_PATCH_ROOT,
    PACK02_UI_EN,
    STRINGS_JSON,
    UI_STRINGS_JSON,
)
from strings_common import pack02_entry_id  # noqa: E402

TEXT_TAG_RE = re.compile(r"<text\b[^>]*/?>")

TEXT_ORIGINAL_ALIASES: dict[str, str] = {
    "exp": "Exp",
}


@dataclass(frozen=True)
class UiStringEntry:
    text: str
    string_no: str
    string_id: str
    file: str
    note: str = ""


@dataclass
class UiStringPatch:
    file: str
    line: int
    text: str
    string_id: str
    string_no: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "file": self.file,
            "line": self.line,
            "text": self.text,
            "string_id": self.string_id,
            "string_no": self.string_no,
        }


def load_ui_strings_config(path: Path) -> dict[str, UiStringEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: dict[str, UiStringEntry] = {}
    for raw in data.get("entries", []):
        entry = UiStringEntry(
            text=raw["text"],
            string_no=str(raw["string_no"]),
            string_id=raw["string_id"],
            file=raw.get("file", ""),
            note=raw.get("note", ""),
        )
        if entry.text in entries:
            raise ValueError(f"duplicate ui_strings text key: {entry.text!r}")
        entries[entry.text] = entry
    return entries


def _expected_catalog_original(text: str) -> str:
    return TEXT_ORIGINAL_ALIASES.get(text, text)


def validate_ui_strings_config(
    config: dict[str, UiStringEntry],
    catalog_entries: dict[str, dict],
) -> list[str]:
    errors: list[str] = []
    for text, entry in sorted(config.items()):
        entry_id = pack02_entry_id(entry.string_no)
        catalog_entry = catalog_entries.get(entry_id)
        if catalog_entry is None:
            errors.append(f"{text!r}: catalog entry missing ({entry_id})")
            continue
        expected_original = _expected_catalog_original(text)
        catalog_original = catalog_entry.get("original", "")
        if catalog_original != expected_original:
            errors.append(
                f"{text!r}: catalog original {catalog_original!r} != expected {expected_original!r}"
            )
        catalog_file = catalog_entry.get("file", "")
        if entry.file and catalog_file != entry.file:
            errors.append(
                f"{text!r}: config file {entry.file!r} != catalog file {catalog_file!r}"
            )
    return errors


def _patch_text_tag(tag: str, entry: UiStringEntry) -> str | None:
    if "string_id=" in tag:
        return None
    if not re.search(rf'\btext="{re.escape(entry.text)}"', tag):
        return None
    if tag.endswith("/>"):
        return tag[:-2] + f' string_id="{entry.string_id}"/>'
    if tag.endswith(">"):
        return tag[:-1] + f' string_id="{entry.string_id}">'
    return None


def _patch_file_content(
    text: str,
    ui_root: Path,
    path: Path,
    config: dict[str, UiStringEntry],
) -> tuple[list[UiStringPatch], str | None]:
    patches: list[UiStringPatch] = []
    lines = text.splitlines(keepends=True)
    changed = False

    for line_idx, line in enumerate(lines):
        new_line = line
        for match in TEXT_TAG_RE.finditer(line):
            tag = match.group(0)
            for entry in config.values():
                patched = _patch_text_tag(tag, entry)
                if patched is None:
                    continue
                new_line = new_line.replace(tag, patched, 1)
                patches.append(
                    UiStringPatch(
                        file=str(path.relative_to(ui_root)),
                        line=line_idx + 1,
                        text=entry.text,
                        string_id=entry.string_id,
                        string_no=entry.string_no,
                    )
                )
                changed = True
                break
        lines[line_idx] = new_line

    if not changed:
        return patches, None
    return patches, "".join(lines)


def apply_ui_string_patches(
    ui_in_dir: Path,
    out_root: Path,
    config: dict[str, UiStringEntry],
    *,
    dry_run: bool = False,
) -> list[UiStringPatch]:
    if not ui_in_dir.is_dir():
        raise FileNotFoundError(ui_in_dir)

    ui_out_dir = out_root / "saves/ui_en"
    all_patches: list[UiStringPatch] = []
    for path in sorted(ui_in_dir.rglob("uil_*.xml")):
        rel = path.relative_to(ui_in_dir)
        patches, new_content = _patch_file_content(
            path.read_text(encoding="utf-8"),
            ui_in_dir,
            path,
            config,
        )
        if new_content is None:
            continue
        all_patches.extend(patches)
        if dry_run:
            continue
        out_path = ui_out_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(new_content, encoding="utf-8")
    return all_patches


def _load_catalog(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"expected entries object in {path}")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-in-dir", type=Path, default=PACK02_UI_EN)
    parser.add_argument("--out-root", type=Path, default=PACK02_PATCH_ROOT)
    parser.add_argument("--config", type=Path, default=UI_STRINGS_JSON)
    parser.add_argument("--strings-json", type=Path, default=STRINGS_JSON)
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip ui_strings.json vs strings.json catalog validation",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--require-changes",
        action="store_true",
        help="Exit 1 when no elements would be patched",
    )
    parser.add_argument(
        "--forbid-changes",
        action="store_true",
        help="Exit 1 when any elements would be patched (idempotency check)",
    )
    args = parser.parse_args()

    config = load_ui_strings_config(args.config.resolve())
    if not args.no_validate:
        catalog = _load_catalog(args.strings_json.resolve())
        errors = validate_ui_strings_config(config, catalog)
        if errors:
            raise SystemExit("ui_strings.json validation failed:\n  " + "\n  ".join(errors))

    patches = apply_ui_string_patches(
        args.ui_in_dir.resolve(),
        args.out_root.resolve(),
        config,
        dry_run=args.dry_run,
    )
    if patches:
        action = "Would patch" if args.dry_run else "Patched"
        print(f"{action} {len(patches)} element(s):")
        for patch in patches:
            print(
                f"  {patch.file}:{patch.line} "
                f'text="{patch.text}" -> string_id="{patch.string_id}" '
                f"(String_No={patch.string_no})"
            )
        files = len({patch.file for patch in patches})
        print(f"files: {files}")
    else:
        print("No changes")

    if args.require_changes and not patches:
        raise SystemExit(1)
    if args.forbid_changes and patches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
