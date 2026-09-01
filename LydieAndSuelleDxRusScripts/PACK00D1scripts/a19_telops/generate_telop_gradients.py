#!/usr/bin/env python3
"""Generate gradient tile PNGs for a19_telop text rendering."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from telop_generate_common import (
    DEFAULT_GRADIENTS_JSON,
    GRADIENTS_OUT_DIR,
    gradient_tile_height,
)


def build_gradient_argv(*, color1: str, color2: str, height: int, out_png: Path) -> list[str]:
    h1 = height // 4
    h2 = height // 2
    return [
        "convert",
        "(",
        "-size",
        f"10x{h1}",
        f"xc:{color1}",
        ")",
        "(",
        "-size",
        f"10x{h2}",
        f"gradient:{color1}-{color2}",
        ")",
        "(",
        "-size",
        f"10x{h1}",
        f"xc:{color2}",
        ")",
        "-append",
        str(out_png),
    ]


def generate_gradients(
    *,
    gradients_json: Path,
    out_dir: Path,
    force: bool,
    dry_run: bool,
) -> int:
    data = json.loads(gradients_json.read_text(encoding="utf-8"))
    gradients: dict[str, dict[str, str]] = data.get("gradients", {})
    if not gradients:
        raise SystemExit(f"no gradients in {gradients_json}")

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    skipped = 0

    for gradient_id in sorted(gradients, key=lambda name: int(name.replace("gradient", ""))):
        colors = gradients[gradient_id]
        color1 = colors["color1"]
        color2 = colors["color2"]
        height = gradient_tile_height(gradient_id)
        out_png = out_dir / f"{gradient_id}.png"

        if out_png.is_file() and not force:
            print(f"skip {out_png.name} (exists)")
            skipped += 1
            continue

        argv = build_gradient_argv(color1=color1, color2=color2, height=height, out_png=out_png)
        print(f"write {out_png.name} ({height}px)")
        if dry_run:
            print("  ", " ".join(argv))
        else:
            subprocess.run(argv, check=True)
        generated += 1

    print(f"gradients: generated={generated}, skipped={skipped}, total={len(gradients)}")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gradients-json",
        type=Path,
        default=DEFAULT_GRADIENTS_JSON,
        help="gradients manifest (default: a19_telops/gradients.json)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=GRADIENTS_OUT_DIR,
        help="output directory for gradient tiles",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing PNGs")
    parser.add_argument("--dry-run", action="store_true", help="print commands only")
    args = parser.parse_args()

    if not args.gradients_json.is_file():
        raise SystemExit(f"gradients json not found: {args.gradients_json}")

    generate_gradients(
        gradients_json=args.gradients_json,
        out_dir=args.out_dir,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
