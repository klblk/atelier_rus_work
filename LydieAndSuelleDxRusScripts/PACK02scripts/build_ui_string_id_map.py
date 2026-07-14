#!/usr/bin/env python3
"""Build String_No -> string_id lookup map from PACK02 str_ui*.xml files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PACK02_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACK02_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import PACK02_TEXT_EN, UI_STRING_ID_MAP_JSON  # noqa: E402

STR_UI_BASE = 6619137
STR_UI_UNTRANSLATED_BASE = 6029313

STR_TAG_RE = re.compile(r"<str\b([^/]*)/>")

KNOWN_SOURCES: dict[str, dict[str, str | int]] = {
    "str_ui.xml": {
        "base_string_no": STR_UI_BASE,
        "id_prefix": "STR_UI",
    },
    "str_ui_untranslated.xml": {
        "base_string_no": STR_UI_UNTRANSLATED_BASE,
        "id_prefix": "STR_UI_UNTRANSLATED",
    },
}


def parse_str_file(path: Path, *, base: int, id_prefix: str) -> tuple[list[dict], dict[str, list[dict]]]:
    entries: list[dict] = []
    by_text: dict[str, list[dict]] = defaultdict(list)
    xml = path.read_text(encoding="utf-8")
    for file_index, attrs in enumerate(STR_TAG_RE.findall(xml)):
        no_m = re.search(r'String_No="(\d+)"', attrs)
        if not no_m:
            continue
        string_no = int(no_m.group(1))
        text_m = re.search(r'Text="([^"]*)"', attrs)
        text = text_m.group(1) if text_m else ""
        index = string_no - base
        if index < 0:
            raise ValueError(f"{path.name}: String_No {string_no} below base {base}")
        string_id = f"{id_prefix}_{index:04d}"
        row = {
            "file_index": file_index,
            "index": index,
            "string_no": str(string_no),
            "string_id": string_id,
            "text": text,
        }
        entries.append(row)
        if text:
            by_text[text].append(row)
    return entries, by_text


def build_map(text_en_dir: Path, files: list[str]) -> dict:
    sources: dict[str, dict] = {}
    by_text_out: dict[str, dict[str, list[dict]]] = {}
    for filename in files:
        meta = KNOWN_SOURCES.get(filename)
        if meta is None:
            raise ValueError(f"unknown source file: {filename!r} (add to KNOWN_SOURCES)")
        path = text_en_dir / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        base = int(meta["base_string_no"])
        id_prefix = str(meta["id_prefix"])
        entries, by_text = parse_str_file(path, base=base, id_prefix=id_prefix)
        sources[filename] = {
            "base_string_no": str(base),
            "id_prefix": id_prefix,
            "entry_count": len(entries),
            "entries": entries,
        }
        by_text_out[filename] = {}
        for text, rows in sorted(by_text.items()):
            tagged = []
            for i, row in enumerate(rows):
                tagged.append(
                    {
                        "string_no": row["string_no"],
                        "string_id": row["string_id"],
                        "index": row["index"],
                        "first": i == 0,
                    }
                )
            by_text_out[filename][text] = tagged
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "by_text": by_text_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--text-en-dir",
        type=Path,
        default=PACK02_TEXT_EN,
        help="Directory with str_ui*.xml (default: PACK02 text_en)",
    )
    parser.add_argument(
        "--files",
        default="str_ui.xml,str_ui_untranslated.xml",
        help="Comma-separated XML filenames to include",
    )
    parser.add_argument("--out", type=Path, default=UI_STRING_ID_MAP_JSON)
    args = parser.parse_args()

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    report = build_map(args.text_en_dir.resolve(), files)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(s["entry_count"] for s in report["sources"].values())
    print(f"Wrote {total} entries from {len(files)} file(s) -> {args.out}")


if __name__ == "__main__":
    main()
