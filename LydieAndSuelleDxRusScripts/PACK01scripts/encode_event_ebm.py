#!/usr/bin/env python3
"""Apply strings.json translations to PACK01 event EBM files with optional kanji encoding."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PACKUTILS_DIR = SCRIPTS_DIR / "PACKutils_scripts"
PACK01_DIR = Path(__file__).resolve().parent
for path in (SCRIPTS_DIR, PACKUTILS_DIR, PACK01_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from catalog import group_pack01_entries, load_catalog  # noqa: E402
from encode_modes import EncodeMode, resolve_output_text  # noqa: E402
from gust_ebm_tools import (  # noqa: E402
    DEFAULT_EBM_LIMIT_BYTES,
    dump_gust_json,
    load_gust_json,
    rebuild_ebm_from_json,
)
from rus_scripts_common import (  # noqa: E402
    GUST_EBM,
    PACK01_EVENT_EBM_EXTRACT,
    PACK01_PATCH_ROOT,
    STRINGS_JSON,
)
from text_encoder import make_encode_fn, utf8_byte_length  # noqa: E402

EXE_PATCHES_DIR = SCRIPTS_DIR / "exe_patches/phys_glyph"
if str(EXE_PATCHES_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_PATCHES_DIR))
from phys_glyph_common import LETTER_CARRIER_MAP_RESOLVED_JSON  # noqa: E402

EBM_JSON_ROOT = PACK01_EVENT_EBM_EXTRACT / "event/event_en"
PATCH_EVENT_EN = PACK01_PATCH_ROOT / "event/event_en"
WORK_DIR = PACK01_PATCH_ROOT / ".work"


@dataclass
class ApplyReport:
    files_written: list[str] = field(default_factory=list)
    messages_applied: int = 0
    skipped_limit: list[dict] = field(default_factory=list)
    dry_run: bool = False


def apply_ebm_file(
    rel_ebm: str,
    file_entries: list[dict],
    *,
    ebm_json_root: Path,
    encode_fn,
    mode: EncodeMode,
    ebm_limit_bytes: int,
    report: ApplyReport,
) -> bool:
    json_src = ebm_json_root / Path(rel_ebm).with_suffix(".json")
    if not json_src.is_file():
        raise FileNotFoundError(f"EBM JSON not found: {json_src}")

    data = load_gust_json(json_src)
    messages = data["messages"]
    pending: list[tuple[int, str]] = []

    for entry in file_entries:
        index = entry["index"]
        output_text = resolve_output_text(
            entry.get("original", ""),
            entry.get("translation", ""),
            mode,
            encode_fn,
        )
        if output_text is None:
            continue
        if encode_fn is not None:
            byte_len = utf8_byte_length(output_text)
            if byte_len > ebm_limit_bytes:
                report.skipped_limit.append(
                    {
                        "path": rel_ebm,
                        "index": index,
                        "reason": f"encoded length {byte_len} > {ebm_limit_bytes}",
                    }
                )
                continue
        current = messages[index].get("msg_string", "")
        if current == output_text:
            continue
        pending.append((index, output_text))

    if not pending:
        return False

    report.messages_applied += len(pending)
    if report.dry_run:
        report.files_written.append(rel_ebm)
        return True

    for index, output_text in pending:
        messages[index]["msg_string"] = output_text

    work_json = WORK_DIR / Path(rel_ebm).with_suffix(".json")
    dump_gust_json(data, work_json)
    work_ebm = rebuild_ebm_from_json(work_json, GUST_EBM)

    out_ebm = PATCH_EVENT_EN / rel_ebm
    out_ebm.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work_ebm, out_ebm)
    report.files_written.append(rel_ebm)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strings-json", type=Path, default=STRINGS_JSON)
    parser.add_argument("--ebm-json-root", type=Path, default=EBM_JSON_ROOT)
    parser.add_argument("--out-root", type=Path, default=PACK01_PATCH_ROOT)
    parser.add_argument(
        "--mode",
        choices=[m.value for m in EncodeMode],
        default=EncodeMode.TRANSLATED.value,
    )
    parser.add_argument("--resolved", type=Path, default=LETTER_CARRIER_MAP_RESOLVED_JSON)
    parser.add_argument(
        "--ebm-limit-bytes",
        type=int,
        default=DEFAULT_EBM_LIMIT_BYTES,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    global PATCH_EVENT_EN, WORK_DIR
    PATCH_EVENT_EN = args.out_root.resolve() / "event/event_en"
    WORK_DIR = args.out_root.resolve() / ".work"

    mode = EncodeMode(args.mode)
    encode_fn = make_encode_fn(args.resolved.resolve(), mode)

    entries = load_catalog(args.strings_json.resolve())
    grouped = group_pack01_entries(entries)
    report = ApplyReport(dry_run=args.dry_run)

    for rel_ebm, file_entries in sorted(grouped.items()):
        apply_ebm_file(
            rel_ebm,
            file_entries,
            ebm_json_root=args.ebm_json_root.resolve(),
            encode_fn=encode_fn,
            mode=mode,
            ebm_limit_bytes=args.ebm_limit_bytes,
            report=report,
        )

    if not report.dry_run and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)

    print(f"mode: {mode.value}")
    print(f"files written: {len(report.files_written)}")
    print(f"messages applied: {report.messages_applied}")
    if report.skipped_limit:
        print(f"skipped (limit): {len(report.skipped_limit)}")
        for item in report.skipped_limit[:10]:
            print(f"  {item['path']}:{item['index']} — {item['reason']}")
        if len(report.skipped_limit) > 10:
            print(f"  ... and {len(report.skipped_limit) - 10} more")


if __name__ == "__main__":
    main()
