#!/usr/bin/env python3
"""Apply recipe condition UI copy limit patch (32/64 -> 128) to steamless exe."""

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
    PATCHED_EXE,
    RECIPE_UI_COPY_LIMIT_PATCHES_JSON,
    STEAMLESS_DEST_EXE,
)

from recipe_ui_copy_limit_patch import (  # noqa: E402
    RECIPE_COPY_LIMIT_PATCHED,
    apply_recipe_ui_copy_limit_patch,
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
        default=RECIPE_UI_COPY_LIMIT_PATCHES_JSON,
        help="JSON manifest output path",
    )
    args = parser.parse_args()

    exe_in = args.exe_in.resolve()
    exe_out = args.exe_out.resolve()
    manifest = args.manifest.resolve()

    if not exe_in.is_file():
        raise SystemExit(f"exe not found: {exe_in}")

    exe = bytearray(exe_in.read_bytes())
    applied = apply_recipe_ui_copy_limit_patch(exe)

    payload = {
        "copy_limit_patched": RECIPE_COPY_LIMIT_PATCHED,
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

    print(f"recipe ui copy limit patches: {len(applied)} sites")
    print(f"wrote {manifest}")
    print(f"wrote {exe_out}")


if __name__ == "__main__":
    main()
