#!/usr/bin/env python3
"""Extract and repack UI .g1t textures listed in PACK00D1scripts/{stem}/patch.json."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PACK00D1SCRIPTS_DIR = Path(__file__).resolve().parent

from texture_repack_common import (  # noqa: E402
    default_ui_g1t_path,
    discover_patched_textures,
    extract_work_ready,
    texture_patch_dir,
)


def run_step(name: str, argv: list[str], *, cwd: Path, dry_run: bool) -> None:
    print(f"\n== {name} ==")
    print(" ".join(argv))
    if not dry_run:
        subprocess.run(argv, cwd=cwd, check=True)


def patch_texture(
    stem: str,
    *,
    scripts_dir: Path,
    force_extract: bool,
    dry_run: bool,
) -> None:
    patch_path = texture_patch_dir(stem) / "patch.json"
    if not patch_path.is_file():
        raise SystemExit(f"patch not found: {patch_path}")

    g1t_path = default_ui_g1t_path(stem)
    if not g1t_path.is_file():
        raise SystemExit(f"g1t not found: {g1t_path}")

    py = sys.executable
    extract_script = PACK00D1SCRIPTS_DIR / "extract_g1t.py"
    repack_script = PACK00D1SCRIPTS_DIR / "repack_g1t.py"

    if force_extract or not extract_work_ready(stem):
        extract_argv = [py, str(extract_script), "--g1t", str(g1t_path)]
        if force_extract:
            extract_argv.append("--force")
        run_step(f"extract_g1t {stem}", extract_argv, cwd=scripts_dir, dry_run=dry_run)
    else:
        print(f"\nSkip extract {stem} (work dir ready)")

    repack_argv = [py, str(repack_script), stem]
    run_step(f"repack_g1t {stem}", repack_argv, cwd=scripts_dir, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "textures",
        nargs="*",
        help="texture stems (e.g. a19_title); omit with --all",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="patch all PACK00D1scripts/*/patch.json",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="recreate extract work dirs even if they already exist",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.all:
        stems = discover_patched_textures()
        if not stems:
            raise SystemExit("no patched textures found (PACK00D1scripts/*/patch.json)")
    elif args.textures:
        stems = list(args.textures)
    else:
        parser.error("pass texture stems or --all")

    scripts_dir = PACK00D1SCRIPTS_DIR.parent
    for stem in stems:
        print(f"\n### UI texture: {stem} ###")
        patch_texture(
            stem,
            scripts_dir=scripts_dir,
            force_extract=args.force_extract,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
