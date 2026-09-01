#!/usr/bin/env python3
"""Generate a19_telop gradient tiles and sprite PNGs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

A19_TELOPS_DIR = Path(__file__).resolve().parent


def run_step(name: str, argv: list[str], *, dry_run: bool) -> None:
    print(f"\n== {name} ==")
    print(" ".join(argv))
    if not dry_run:
        subprocess.run(argv, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing PNGs")
    parser.add_argument("--dry-run", action="store_true", help="print commands only")
    parser.add_argument(
        "--only-index",
        type=int,
        default=None,
        help="render a single sprite by index (gradients still generated fully)",
    )
    parser.add_argument(
        "--skip-gradients",
        action="store_true",
        help="skip gradient tile generation",
    )
    args = parser.parse_args()

    py = sys.executable
    gradients_script = A19_TELOPS_DIR / "generate_telop_gradients.py"
    sprites_script = A19_TELOPS_DIR / "generate_telop_sprites.py"

    if not args.skip_gradients:
        gradients_argv = [py, str(gradients_script)]
        if args.force:
            gradients_argv.append("--force")
        if args.dry_run:
            gradients_argv.append("--dry-run")
        run_step("generate_telop_gradients", gradients_argv, dry_run=args.dry_run)

    sprites_argv = [py, str(sprites_script)]
    if args.force:
        sprites_argv.append("--force")
    if args.dry_run:
        sprites_argv.append("--dry-run")
    if args.only_index is not None:
        sprites_argv.extend(["--only-index", str(args.only_index)])
    run_step("generate_telop_sprites", sprites_argv, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
