#!/usr/bin/env python3
"""Extract UI .g1t texture to texture.json + atlas/sprite PNGs."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from texture_repack_common import (
    EXTRACT_G1T_ROOT,
    apply_pixel_coords,
    crop_and_save_sprites,
    find_uis_xml,
    load_dds_pages,
    parse_uis_xml,
    save_atlas_pngs,
    unpack_g1t,
    write_texture_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g1t", type=Path, required=True, help="Path to .g1t file")
    parser.add_argument(
        "--xml",
        type=Path,
        default=None,
        help="uis_gen_*.xml (default: auto-detect in PACK02 extract)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Work directory (default: build/extract_g1t/<g1t_stem>/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="recreate work directory even if it already exists",
    )
    args = parser.parse_args()

    g1t_path = args.g1t.resolve()
    if not g1t_path.is_file():
        raise SystemExit(f"g1t not found: {g1t_path}")

    xml_path = args.xml.resolve() if args.xml else find_uis_xml(g1t_path)
    if xml_path is None:
        raise SystemExit(f"No uis_gen XML found for {g1t_path.name}; pass --xml")
    if not xml_path.is_file():
        raise SystemExit(f"xml not found: {xml_path}")

    work_dir = (args.work_dir or EXTRACT_G1T_ROOT / g1t_path.stem).resolve()
    if args.force and work_dir.is_dir():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    dds_dir = unpack_g1t(g1t_path, work_dir)
    pages = load_dds_pages(dds_dir)
    atlases = save_atlas_pngs(pages, work_dir)

    resolution_hd, sprites = parse_uis_xml(xml_path, g1t_path.name)
    apply_pixel_coords(sprites, pages)
    crop_and_save_sprites(sprites, pages, work_dir)

    texture_json = write_texture_json(
        work_dir=work_dir,
        g1t_path=g1t_path,
        xml_path=xml_path,
        resolution_hd=resolution_hd,
        atlases=atlases,
        sprites=sprites,
    )

    print(f"Work dir: {work_dir}")
    print(f"Texture JSON: {texture_json}")
    print(f"XML: {xml_path}")
    print(f"Atlases: {len(atlases)}")
    print(f"Sprites: {len(sprites)}")


if __name__ == "__main__":
    main()
