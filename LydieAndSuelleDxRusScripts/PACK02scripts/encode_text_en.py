#!/usr/bin/env python3
"""Apply strings.json translations to PACK02 text_en XML with optional kanji encoding."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PACKUTILS_DIR = SCRIPTS_DIR / "PACKutils_scripts"
PACK02_DIR = Path(__file__).resolve().parent
for path in (SCRIPTS_DIR, PACKUTILS_DIR, PACK02_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from catalog import group_pack02_entries, load_catalog  # noqa: E402
from encode_modes import EncodeMode, resolve_output_text  # noqa: E402
from pack02_xml import (  # noqa: E402
    DEFAULT_DIALOG_LIMIT_BYTES,
    STRCOMBINEALL_NAME,
    Pack02XmlCache,
    cached_match_text,
    npc_mess_file,
    patch_catalog_cached,
)
from rus_scripts_common import PACK02_PATCH_ROOT, PACK02_TEXT_EN, STRINGS_JSON  # noqa: E402
from text_encoder import make_encode_fn, utf8_byte_length  # noqa: E402

EXE_PATCHES_DIR = SCRIPTS_DIR / "exe_patches/phys_glyph"
if str(EXE_PATCHES_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_PATCHES_DIR))
from phys_glyph_common import LETTER_CARRIER_MAP_RESOLVED_JSON  # noqa: E402


@dataclass
class ApplyReport:
    strings_applied: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    skipped_limit: list[dict] = field(default_factory=list)
    dry_run: bool = False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strings-json", type=Path, default=STRINGS_JSON)
    parser.add_argument("--text-en-dir", type=Path, default=PACK02_TEXT_EN)
    parser.add_argument("--out-root", type=Path, default=PACK02_PATCH_ROOT)
    parser.add_argument(
        "--mode",
        choices=[m.value for m in EncodeMode],
        default=EncodeMode.TRANSLATED.value,
    )
    parser.add_argument("--resolved", type=Path, default=LETTER_CARRIER_MAP_RESOLVED_JSON)
    parser.add_argument(
        "--dialog-limit-bytes",
        type=int,
        default=DEFAULT_DIALOG_LIMIT_BYTES,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    mode = EncodeMode(args.mode)
    encode_fn = make_encode_fn(args.resolved.resolve(), mode)

    entries = group_pack02_entries(load_catalog(args.strings_json.resolve()))
    report = ApplyReport(dry_run=args.dry_run)

    cache = Pack02XmlCache(args.text_en_dir.resolve())
    out_dir = args.out_root.resolve() / "saves/text_en"
    pending_files: set[str] = set()

    for entry in sorted(entries, key=lambda item: item.get("string_no", "")):
        string_no = entry["string_no"]
        layer_file = entry.get("file", "")
        output_text = resolve_output_text(
            entry.get("original", ""),
            entry.get("translation", ""),
            mode,
            encode_fn,
        )
        if output_text is None:
            continue
        if encode_fn is not None and layer_file and npc_mess_file(layer_file):
            byte_len = utf8_byte_length(output_text)
            if byte_len > args.dialog_limit_bytes:
                report.skipped_limit.append(
                    {
                        "string_no": string_no,
                        "file": layer_file,
                        "reason": f"encoded length {byte_len} > {args.dialog_limit_bytes}",
                    }
                )
                continue
        if not layer_file:
            raise SystemExit(f"String_No={string_no}: missing layer file in catalog")
        if cached_match_text(cache, string_no, output_text, layer_file):
            continue
        if report.dry_run:
            report.strings_applied.append(string_no)
            pending_files.add(layer_file)
            pending_files.add(STRCOMBINEALL_NAME)
            continue
        patch_catalog_cached(cache, string_no, output_text, layer_file)
        report.strings_applied.append(string_no)

    if report.dry_run:
        report.files_written = sorted(pending_files)
    else:
        report.files_written = cache.flush(out_dir)

    print(f"mode: {mode.value}")
    print(f"strings applied: {len(report.strings_applied)}")
    print(f"files written: {len(report.files_written)}")
    if report.skipped_limit:
        print(f"skipped (limit): {len(report.skipped_limit)}")
        for item in report.skipped_limit[:10]:
            print(f"  {item['string_no']} ({item['file']}) — {item['reason']}")
        if len(report.skipped_limit) > 10:
            print(f"  ... and {len(report.skipped_limit) - 10} more")


if __name__ == "__main__":
    main()
