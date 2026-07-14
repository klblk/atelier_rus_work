#!/usr/bin/env python3
"""Apply EBM message buffer length patch (400 -> 800) to steamless exe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LENGTH_PATCHES_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = LENGTH_PATCHES_DIR.parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    EBM_LENGTH_PATCHES_JSON,
    PATCHED_EXE,
    STEAMLESS_DEST_EXE,
)

from ebm_length_patch import (  # noqa: E402
    EBM_BUF_MAX_PATCHED,
    EBM_BUF_MAX_VANILLA,
    apply_ebm_length_patch,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exe-in",
        type=Path,
        default=STEAMLESS_DEST_EXE,
        help="Steamless-unpacked input exe",
    )
    parser.add_argument(
        "--exe-out",
        type=Path,
        default=PATCHED_EXE,
        help="Patched output exe",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=EBM_LENGTH_PATCHES_JSON,
        help="JSON manifest output path",
    )
    args = parser.parse_args()

    exe_in = args.exe_in.resolve()
    exe_out = args.exe_out.resolve()
    manifest = args.manifest.resolve()

    if not exe_in.is_file():
        raise SystemExit(f"exe not found: {exe_in}")

    exe = bytearray(exe_in.read_bytes())
    applied = apply_ebm_length_patch(exe)

    payload = {
        "buf_limit_vanilla": EBM_BUF_MAX_VANILLA,
        "buf_limit_patched": EBM_BUF_MAX_PATCHED,
        "sites_count": len(applied),
        "patches": applied,
    }

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    exe_out.parent.mkdir(parents=True, exist_ok=True)
    exe_out.write_bytes(exe)

    print(f"ebm length patches: {len(applied)} sites")
    print(f"wrote {manifest}")
    print(f"wrote {exe_out}")


if __name__ == "__main__":
    main()
