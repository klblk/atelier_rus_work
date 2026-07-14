#!/usr/bin/env python3
"""Apply exe patches to steamless-unpacked Atelier Lydie & Suelle DX."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    DIALOG_LENGTH_PATCHES_JSON,
    EBM_LENGTH_PATCHES_JSON,
    EXE_BUILD_DIR,
    EXE_PATCHES_DIR,
    PATCH_CHAIN_WORK_EXE,
    PATCHED_EXE,
    QUEST_ETC_COPY_LIMIT_PATCHES_JSON,
    RECIPE_UI_COPY_LIMIT_PATCHES_JSON,
    SCRIPTS_DIR as _SCRIPTS_DIR,
    STEAMLESS_DEST_EXE,
)

LENGTH_PATCHES_DIR = EXE_PATCHES_DIR / "length_patches"
if str(LENGTH_PATCHES_DIR) not in sys.path:
    sys.path.insert(0, str(LENGTH_PATCHES_DIR))

from dialog_length_patch import (  # noqa: E402
    DIALOG_BUF_MAX_PATCHED,
    DIALOG_BUF_MAX_VANILLA,
    apply_dialog_length_patch,
)
from ebm_length_patch import (  # noqa: E402
    EBM_BUF_MAX_PATCHED,
    EBM_BUF_MAX_VANILLA,
    apply_ebm_length_patch,
)
from recipe_ui_copy_limit_patch import (  # noqa: E402
    RECIPE_COPY_LIMIT_PATCHED,
    apply_recipe_ui_copy_limit_patch,
)
from quest_etc_copy_limit_patch import (  # noqa: E402
    QUEST_COPY_LIMIT_PATCHED,
    apply_quest_etc_copy_limit_patch,
)


def write_length_manifest(path: Path, *, vanilla: int, patched: int, applied: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "buf_limit_vanilla": vanilla,
                "buf_limit_patched": patched,
                "sites_count": len(applied),
                "patches": applied,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_recipe_manifest(path: Path, *, patched: int, applied: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "copy_limit_patched": patched,
                "sites_count": len(applied),
                "patches": applied,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_phys_glyph(exe_in: Path, exe_out: Path, *, force: bool) -> None:
    phys_patch = EXE_PATCHES_DIR / "phys_glyph/patch_phys_glyph_exe.py"
    print("\n== phys_glyph ==")
    cmd = [
        sys.executable,
        str(phys_patch),
        "--exe-in",
        str(exe_in),
        "--exe-out",
        str(exe_out),
    ]
    if force:
        cmd.append("--force")
    subprocess.run(cmd, cwd=_SCRIPTS_DIR, check=True)


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
        "--skip",
        action="store_true",
        help="Skip if output exe already exists",
    )
    parser.add_argument(
        "--phys-glyph",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply phys_glyph patch (default: on)",
    )
    parser.add_argument(
        "--ebm-length",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply EBM buffer length patch 400->800 (default: on)",
    )
    parser.add_argument(
        "--dialog-length",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply dialog buffer length patch 256->512 (default: on)",
    )
    parser.add_argument(
        "--recipe-ui-copy-limit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply recipe UI copy limit patch 32/64->128 (default: on)",
    )
    parser.add_argument(
        "--quest-etc-copy-limit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply quest objective UI copy limit patch 64->128 (default: on)",
    )
    args = parser.parse_args()

    if (
        not args.phys_glyph
        and not args.ebm_length
        and not args.dialog_length
        and not args.recipe_ui_copy_limit
        and not args.quest_etc_copy_limit
    ):
        raise SystemExit("no patches selected (all --no-* flags set)")

    exe_in = args.exe_in.resolve()
    exe_out = args.exe_out.resolve()

    if not exe_in.is_file():
        raise SystemExit(f"exe not found: {exe_in}")

    if args.skip and exe_out.is_file():
        print(f"Skip (exists): {exe_out}")
        return

    force = not args.skip
    length_enabled = (
        args.ebm_length
        or args.dialog_length
        or args.recipe_ui_copy_limit
        or args.quest_etc_copy_limit
    )

    if length_enabled:
        work = bytearray(exe_in.read_bytes())

        if args.ebm_length:
            print("\n== ebm_length ==")
            applied = apply_ebm_length_patch(work)
            write_length_manifest(
                EBM_LENGTH_PATCHES_JSON,
                vanilla=EBM_BUF_MAX_VANILLA,
                patched=EBM_BUF_MAX_PATCHED,
                applied=applied,
            )
            print(f"ebm length patches: {len(applied)} sites")
            print(f"wrote {EBM_LENGTH_PATCHES_JSON}")

        if args.dialog_length:
            print("\n== dialog_length ==")
            applied = apply_dialog_length_patch(work)
            write_length_manifest(
                DIALOG_LENGTH_PATCHES_JSON,
                vanilla=DIALOG_BUF_MAX_VANILLA,
                patched=DIALOG_BUF_MAX_PATCHED,
                applied=applied,
            )
            print(f"dialog length patches: {len(applied)} sites")
            print(f"wrote {DIALOG_LENGTH_PATCHES_JSON}")

        if args.recipe_ui_copy_limit:
            print("\n== recipe_ui_copy_limit ==")
            applied = apply_recipe_ui_copy_limit_patch(work)
            write_recipe_manifest(
                RECIPE_UI_COPY_LIMIT_PATCHES_JSON,
                patched=RECIPE_COPY_LIMIT_PATCHED,
                applied=applied,
            )
            print(f"recipe ui copy limit patches: {len(applied)} sites")
            print(f"wrote {RECIPE_UI_COPY_LIMIT_PATCHES_JSON}")

        if args.quest_etc_copy_limit:
            print("\n== quest_etc_copy_limit ==")
            applied = apply_quest_etc_copy_limit_patch(work)
            write_recipe_manifest(
                QUEST_ETC_COPY_LIMIT_PATCHES_JSON,
                patched=QUEST_COPY_LIMIT_PATCHED,
                applied=applied,
            )
            print(f"quest etc copy limit patches: {len(applied)} sites")
            print(f"wrote {QUEST_ETC_COPY_LIMIT_PATCHES_JSON}")

        if args.phys_glyph:
            EXE_BUILD_DIR.mkdir(parents=True, exist_ok=True)
            PATCH_CHAIN_WORK_EXE.write_bytes(work)
            try:
                run_phys_glyph(PATCH_CHAIN_WORK_EXE, exe_out, force=force)
            finally:
                PATCH_CHAIN_WORK_EXE.unlink(missing_ok=True)
        else:
            exe_out.parent.mkdir(parents=True, exist_ok=True)
            exe_out.write_bytes(work)
            print(f"wrote {exe_out}")
    elif args.phys_glyph:
        run_phys_glyph(exe_in, exe_out, force=force)


if __name__ == "__main__":
    main()
