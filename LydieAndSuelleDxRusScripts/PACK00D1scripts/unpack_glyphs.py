#!/usr/bin/env python3
"""Extract PNG glyphs from a .g1t atlas using atlas_table.csv coordinates."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from font_pack_common import (
    ATLAS_TABLE_CSV,
    DEFAULT_TEXTURE_G1T,
    UNPACK_GLYPHS_DIR,
    atlas_dds_from_g1t,
    g1t_work_dir_for,
    load_atlas_table,
)


def unpack_glyphs(
    *,
    g1t_path: Path,
    table_path: Path,
    out_dir: Path = UNPACK_GLYPHS_DIR,
    g1t_work: Path | None = None,
    force: bool = False,
) -> None:
    from PIL import Image

    if not table_path.is_file():
        raise SystemExit(f"table not found: {table_path}")
    if not g1t_path.is_file():
        raise SystemExit(f"g1t not found: {g1t_path}")

    if g1t_work is None:
        g1t_work = g1t_work_dir_for(g1t_path)

    if out_dir.exists():
        if not force:
            existing = list(out_dir.glob("*.png"))
            if existing:
                raise SystemExit(f"{out_dir} exists with {len(existing)} PNG(s); use --force")
        else:
            shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dds_path = atlas_dds_from_g1t(g1t_path, g1t_work, force=force)
    rows = load_atlas_table(table_path)

    with Image.open(dds_path) as atlas_im:
        atlas = atlas_im.convert("RGBA")
        aw, ah = atlas.size

        for row in rows:
            x, y, w, h = row["x"], row["y"], row["w"], row["h"]
            if x < 0 or y < 0 or x + w > aw or y + h > ah:
                raise SystemExit(
                    f"crop out of bounds for {row['png']}: "
                    f"({x},{y})+({w}x{h}) in {aw}x{ah}"
                )
            crop = atlas.crop((x, y, x + w, y + h))
            if crop.size != (w, h):
                print(
                    f"warning: {row['png']} crop size {crop.size} != table ({w}, {h})"
                )
            crop.save(out_dir / row["png"])

    manifest = {
        "g1t": str(g1t_path),
        "table": str(table_path),
        "g1t_work": str(g1t_work),
        "dds": str(dds_path),
        "glyph_count": len(rows),
        "out_dir": str(out_dir),
    }
    (out_dir / "unpack_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Extracted {len(rows)} glyphs -> {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g1t", type=Path, default=DEFAULT_TEXTURE_G1T)
    parser.add_argument("--table", type=Path, default=ATLAS_TABLE_CSV)
    parser.add_argument("--out", type=Path, default=UNPACK_GLYPHS_DIR)
    parser.add_argument(
        "--g1t-work",
        type=Path,
        default=None,
        help="g1t unpack directory (default: build/{g1t_stem}_work)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="recreate output directory and re-unpack g1t",
    )
    args = parser.parse_args()
    unpack_glyphs(
        g1t_path=args.g1t.resolve(),
        table_path=args.table.resolve(),
        out_dir=args.out.resolve(),
        g1t_work=args.g1t_work.resolve() if args.g1t_work else None,
        force=args.force,
    )


if __name__ == "__main__":
    main()
