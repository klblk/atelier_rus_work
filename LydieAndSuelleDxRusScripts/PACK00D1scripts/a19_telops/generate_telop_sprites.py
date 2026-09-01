#!/usr/bin/env python3
"""Generate telop sprite PNGs from sprites.json (non-empty text only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from telop_generate_common import (
    DEFAULT_FONT,
    DEFAULT_GRADIENTS_JSON,
    DEFAULT_SPRITES_JSON,
    GRADIENTS_OUT_DIR,
    SPRITES_OUT_DIR,
    default_pointsize,
    escape_im_text,
)


def build_sprite_argv(
    *,
    width: int,
    height: int,
    font: Path,
    pointsize: int,
    stroke: str,
    text: str,
    gradient_png: Path,
    out_png: Path,
) -> list[str]:
    escaped = escape_im_text(text)
    return [
        "convert",
        "-size",
        f"{width}x{height}",
        "xc:none",
        "-gravity",
        "Center",
        "-font",
        str(font),
        "-pointsize",
        str(pointsize),
        "-stroke",
        stroke,
        "-strokewidth",
        "5",
        "-fill",
        stroke,
        "-annotate",
        "-1-1",
        escaped,
        "-annotate",
        "+1-1",
        escaped,
        "-annotate",
        "-1+1",
        escaped,
        "-annotate",
        "+1+1",
        escaped,
        "-annotate",
        "+0+0",
        escaped,
        "-stroke",
        "none",
        "-tile",
        str(gradient_png),
        "-annotate",
        "-1+0",
        escaped,
        "-annotate",
        "+1+0",
        escaped,
        "-annotate",
        "+0-1",
        escaped,
        "-annotate",
        "+0+1",
        escaped,
        "-annotate",
        "+0+0",
        escaped,
        str(out_png),
    ]


def generate_sprites(
    *,
    sprites_json: Path,
    gradients_json: Path,
    gradients_dir: Path,
    out_dir: Path,
    font: Path,
    pointsize: int | None,
    only_index: int | None,
    force: bool,
    dry_run: bool,
) -> int:
    sprites_doc = json.loads(sprites_json.read_text(encoding="utf-8"))
    gradients_doc = json.loads(gradients_json.read_text(encoding="utf-8"))
    gradients: dict[str, dict[str, str]] = gradients_doc.get("gradients", {})

    sprites = sprites_doc.get("sprites", [])
    if only_index is not None:
        sprites = [s for s in sprites if s.get("index") == only_index]
        if not sprites:
            raise SystemExit(f"sprite index not found: {only_index}")

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    skipped = 0

    for sprite in sprites:
        text = (sprite.get("text") or "").strip()
        if not text:
            continue

        gradient_id = (sprite.get("gradient") or "").strip()
        if not gradient_id:
            raise SystemExit(f"sprite {sprite.get('id')}: empty gradient")
        if gradient_id not in gradients:
            raise SystemExit(f"sprite {sprite.get('id')}: unknown gradient {gradient_id!r}")

        gradient_png = gradients_dir / f"{gradient_id}.png"
        if not gradient_png.is_file():
            raise SystemExit(
                f"missing {gradient_png}; run generate_telop_gradients.py first"
            )

        sprite_id = sprite["id"]
        width = int(sprite["w"])
        height = int(sprite["h"])
        stroke = gradients[gradient_id]["stroke"]
        size = pointsize if pointsize is not None else default_pointsize(height)
        out_png = out_dir / f"{sprite_id}.png"

        if out_png.is_file() and not force:
            print(f"skip {out_png.name} (exists)")
            skipped += 1
            continue

        argv = build_sprite_argv(
            width=width,
            height=height,
            font=font,
            pointsize=size,
            stroke=stroke,
            text=text,
            gradient_png=gradient_png,
            out_png=out_png,
        )
        print(f"write {out_png.name} ({width}x{height}, {gradient_id}, pt={size})")
        if dry_run:
            print("  ", " ".join(argv))
        else:
            subprocess.run(argv, check=True)
        generated += 1

    print(f"sprites: generated={generated}, skipped={skipped}")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sprites-json",
        type=Path,
        default=DEFAULT_SPRITES_JSON,
        help="sprites manifest (default: a19_telops/sprites.json)",
    )
    parser.add_argument(
        "--gradients-json",
        type=Path,
        default=DEFAULT_GRADIENTS_JSON,
        help="gradients manifest (default: a19_telops/gradients.json)",
    )
    parser.add_argument(
        "--gradients-dir",
        type=Path,
        default=GRADIENTS_OUT_DIR,
        help="directory with gradient tile PNGs",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SPRITES_OUT_DIR,
        help="output directory for sprite PNGs",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=DEFAULT_FONT,
        help="TTF font for rendering",
    )
    parser.add_argument(
        "--pointsize",
        type=int,
        default=None,
        help="font size (default: 56 for h=96, 112 for h=192)",
    )
    parser.add_argument(
        "--only-index",
        type=int,
        default=None,
        help="render a single sprite by index",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing PNGs")
    parser.add_argument("--dry-run", action="store_true", help="print commands only")
    args = parser.parse_args()

    for path, label in (
        (args.sprites_json, "sprites json"),
        (args.gradients_json, "gradients json"),
        (args.font, "font"),
    ):
        if not path.is_file():
            raise SystemExit(f"{label} not found: {path}")

    generate_sprites(
        sprites_json=args.sprites_json,
        gradients_json=args.gradients_json,
        gradients_dir=args.gradients_dir,
        out_dir=args.out_dir,
        font=args.font,
        pointsize=args.pointsize,
        only_index=args.only_index,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
