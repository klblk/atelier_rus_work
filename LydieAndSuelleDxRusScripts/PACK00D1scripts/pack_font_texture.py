#!/usr/bin/env python3
"""Paste Cyrillic glyphs into vanilla font atlas, BC3-patch, repack .g1t."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from font_pack_common import (
    ATLAS_H,
    ATLAS_W,
    ATLAS_TABLE_CSV,
    COMPRESS_BC3,
    DEFAULT_G1T_WORK,
    DEFAULT_START_X,
    DEFAULT_START_Y,
    GLYPHS_DIR,
    GUST_G1T,
    MAINFONT_PACK_WORK_DIR,
    PACK00D1_PATCHED_MAINFONT_G1T,
    ROOT,
    TARGET_LETTERS,
    VANILLA_G1T,
    VANILLA_G1T_SIZE,
    bbox_from_placed,
    glyphs_by_case_from_letters,
    layout_rows,
)
from unpack_g1t import unpack_g1t


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_g1t_work(g1t_work: Path, *, force_unpack: bool) -> None:
    dds = g1t_work / "000.dds"
    if dds.is_file() and not force_unpack:
        return
    unpack_g1t(VANILLA_G1T, g1t_work, force=force_unpack or dds.is_file())


def pack_font_texture(
    *,
    g1t_work: Path = DEFAULT_G1T_WORK,
    glyphs_dir: Path = GLYPHS_DIR,
    work_dir: Path = MAINFONT_PACK_WORK_DIR,
    patched_g1t: Path = PACK00D1_PATCHED_MAINFONT_G1T,
    atlas_table: Path = ATLAS_TABLE_CSV,
    start_x: int = DEFAULT_START_X,
    start_y: int = DEFAULT_START_Y,
    compressor: Path = COMPRESS_BC3,
    force: bool = False,
    skip_bc3: bool = False,
) -> None:
    from PIL import Image

    if patched_g1t.is_file() and not force:
        print(f"Skip (exists): {patched_g1t}")
        return

    if len(TARGET_LETTERS) != 69:
        raise SystemExit(f"expected 69 target letters, got {len(TARGET_LETTERS)}")

    ensure_g1t_work(g1t_work, force_unpack=force)
    van_dds = g1t_work / "000.dds"
    if not van_dds.is_file():
        raise SystemExit(f"missing {van_dds}; run: python3 unpack_g1t.py")

    by_case = glyphs_by_case_from_letters(glyphs_dir=glyphs_dir)
    placed = layout_rows(by_case, start_x=start_x, start_y=start_y)
    if len(placed) != 69:
        raise SystemExit(f"expected 69 placed glyphs, got {len(placed)}")

    atlas = Image.open(van_dds).convert("RGBA")
    if atlas.size != (ATLAS_W, ATLAS_H):
        raise SystemExit(f"unexpected atlas size {atlas.size}, expected {ATLAS_W}x{ATLAS_H}")

    for g in placed:
        img = Image.open(glyphs_dir / g["png"]).convert("RGBA")
        if img.size != (g["w"], g["h"]):
            raise SystemExit(f"size mismatch for {g['png']}: {img.size} vs {g['w']}x{g['h']}")
        atlas.paste(img, (g["x"], g["y"]), img)

    work_dir.mkdir(parents=True, exist_ok=True)
    merged_dds = work_dir / "merged_000.dds"
    merged_rgba = work_dir / "merged.rgba"
    atlas.save(merged_dds)
    merged_rgba.write_bytes(atlas.tobytes())

    x0, y0, x1, y1 = bbox_from_placed(placed)
    patched_dds = work_dir / "000_patched.dds"
    g1t_archive = g1t_work.parent / f"{g1t_work.name}.g1t"

    if skip_bc3:
        print("skip_bc3: wrote merged preview only (no g1t repack)")
    else:
        if not compressor.is_file():
            raise SystemExit(
                f"compressor not found: {compressor}\n"
                "Build: make -C tools/compress_bc3_region_src\n"
                "Or pass --skip-bc3 to validate layout/composite only."
            )
        subprocess.run(
            [
                str(compressor),
                str(van_dds),
                str(patched_dds),
                str(merged_rgba),
                str(ATLAS_W),
                str(ATLAS_H),
                str(x0),
                str(y0),
                str(x1),
                str(y1),
            ],
            check=True,
        )
        shutil.copy2(patched_dds, van_dds)

        if not GUST_G1T.is_file():
            raise SystemExit(f"gust_g1t not found: {GUST_G1T}")
        subprocess.run([str(GUST_G1T), str(g1t_work)], check=True, cwd=g1t_work.parent)
        if not g1t_archive.is_file():
            raise SystemExit(f"repack failed: missing {g1t_archive}")

        patched_g1t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(g1t_archive, patched_g1t)

        new_size = patched_g1t.stat().st_size
        if new_size != VANILLA_G1T_SIZE:
            raise SystemExit(f"g1t size mismatch: {new_size} != {VANILLA_G1T_SIZE}")

    atlas_table.parent.mkdir(parents=True, exist_ok=True)
    with atlas_table.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["png", "w", "h", "x", "y", "letter"])
        writer.writeheader()
        for g in placed:
            writer.writerow(
                {
                    "png": g["png"],
                    "w": g["w"],
                    "h": g["h"],
                    "x": g["x"],
                    "y": g["y"],
                    "letter": g["letter"],
                }
            )

    manifest = {
        "glyph_count": len(placed),
        "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "start": {"x": start_x, "y": start_y},
        "vanilla_g1t": str(VANILLA_G1T.relative_to(ROOT)),
        "vanilla_g1t_sha256": sha256_file(VANILLA_G1T),
        "vanilla_g1t_size": VANILLA_G1T_SIZE,
        "compressor": str(compressor.relative_to(ROOT))
        if compressor.is_file()
        else str(compressor),
    }
    if not skip_bc3 and patched_g1t.is_file():
        manifest["patched_g1t"] = str(patched_g1t.relative_to(ROOT))
        manifest["patched_g1t_sha256"] = sha256_file(patched_g1t)
        manifest["patched_g1t_size"] = patched_g1t.stat().st_size

    manifest_path = work_dir / "pack_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Placed {len(placed)} glyphs, bbox=({x0},{y0})-({x1},{y1})")
    print(f"Wrote {merged_dds}")
    print(f"Wrote {atlas_table}")
    print(f"Wrote {manifest_path}")
    if not skip_bc3:
        print(f"Wrote {patched_g1t} ({patched_g1t.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g1t-work", type=Path, default=DEFAULT_G1T_WORK)
    parser.add_argument("--glyphs", type=Path, default=GLYPHS_DIR)
    parser.add_argument("--work-dir", type=Path, default=MAINFONT_PACK_WORK_DIR)
    parser.add_argument("--patched-g1t", type=Path, default=PACK00D1_PATCHED_MAINFONT_G1T)
    parser.add_argument("--atlas-table", type=Path, default=ATLAS_TABLE_CSV)
    parser.add_argument("--start-x", type=int, default=DEFAULT_START_X)
    parser.add_argument("--start-y", type=int, default=DEFAULT_START_Y)
    parser.add_argument("--compressor", type=Path, default=COMPRESS_BC3)
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild even if patched g1t exists (also re-unpack vanilla)",
    )
    parser.add_argument(
        "--skip-bc3",
        action="store_true",
        help="composite + atlas_table only (no BC3 / g1t repack)",
    )
    args = parser.parse_args()
    pack_font_texture(
        g1t_work=args.g1t_work.resolve(),
        glyphs_dir=args.glyphs.resolve(),
        work_dir=args.work_dir.resolve(),
        patched_g1t=args.patched_g1t.resolve(),
        atlas_table=args.atlas_table.resolve(),
        start_x=args.start_x,
        start_y=args.start_y,
        compressor=args.compressor.resolve(),
        force=args.force,
        skip_bc3=args.skip_bc3,
    )


if __name__ == "__main__":
    main()
