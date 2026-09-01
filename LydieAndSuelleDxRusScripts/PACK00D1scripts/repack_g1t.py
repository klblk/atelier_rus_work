#!/usr/bin/env python3
"""Repack UI .g1t from texture.json + sparse patch.json."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

from texture_repack_common import (
    EXTRACT_G1T_ROOT,
    PACK00D1_PATCH_ROOT,
    PACK02_PATCH_ROOT,
    ROOT,
    TEXTURE_JSON_NAME,
    compress_atlas_page,
    load_texture_json,
    merge_sprites,
    patched_sprites_bbox,
    rebuild_atlas_page,
    repack_g1t_archive,
    resolve_work_path,
    texture_patch_dir,
    update_uis_xml_uvwh,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("texture", help="Texture stem, e.g. a19_title")
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help="texture.json from extract (default: build/extract_g1t/<texture>/texture.json)",
    )
    parser.add_argument(
        "--patch",
        type=Path,
        default=None,
        help="sparse patch.json (default: PACK00D1scripts/<texture>/patch.json)",
    )
    parser.add_argument(
        "--xml",
        type=Path,
        default=None,
        help="source uis_gen XML (default: path from texture.json)",
    )
    args = parser.parse_args()

    texture_stem = args.texture
    patch_dir = texture_patch_dir(texture_stem)
    base_path = (args.base or EXTRACT_G1T_ROOT / texture_stem / TEXTURE_JSON_NAME).resolve()
    patch_path = (args.patch or patch_dir / "patch.json").resolve()

    if not base_path.is_file():
        raise SystemExit(f"base json not found: {base_path}")
    if not patch_path.is_file():
        raise SystemExit(f"patch json not found: {patch_path}")

    base = load_texture_json(base_path)
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    patch_sprites = patch.get("sprites", [])
    if not isinstance(patch_sprites, list):
        raise SystemExit("patch.json must contain a sprites array")

    work_dir = resolve_work_path(Path(base["work_dir"]), ".")
    if not work_dir.is_dir():
        work_dir = base_path.parent

    g1t_stem = Path(base["g1t"]).stem
    dds_dir = work_dir / "source" / g1t_stem
    if not dds_dir.is_dir():
        raise SystemExit(f"source dds dir not found: {dds_dir}; run extract_g1t.py first")

    xml_path = args.xml.resolve() if args.xml else (ROOT / base["xml"]).resolve()
    if base.get("xml_pack_relpath"):
        patch_xml = PACK02_PATCH_ROOT / base["xml_pack_relpath"]
        if patch_xml.is_file():
            xml_path = patch_xml.resolve()
            if "uis_a19_telop.xml" in base["xml_pack_relpath"]:
                print(f"using shared telop XML: {xml_path}")
    if not xml_path.is_file():
        raise SystemExit(f"xml not found: {xml_path}")

    final_sprites = merge_sprites(base["sprites"], patch_sprites, work_dir, patch_dir)
    sprites_by_atlas: dict[int, list[dict]] = defaultdict(list)
    for sprite in final_sprites:
        sprites_by_atlas[int(sprite["atlas"])].append(sprite)

    patched_ids = {item["id"] for item in patch_sprites}
    pages_to_compress: set[int] = set()
    for sprite in base["sprites"]:
        if sprite["id"] in patched_ids:
            pages_to_compress.add(int(sprite["atlas"]))

    atlas_sizes = {int(item["id"]): (int(item["width"]), int(item["height"])) for item in base["atlases"]}

    for atlas in base["atlases"]:
        atlas_id = int(atlas["id"])
        if atlas_id not in pages_to_compress:
            continue
        if atlas_id not in sprites_by_atlas:
            continue
        vanilla_atlas = resolve_work_path(work_dir, atlas["png"])
        base_on_page = [s for s in base["sprites"] if int(s["atlas"]) == atlas_id]
        rebuilt = rebuild_atlas_page(
            vanilla_atlas,
            base_on_page,
            sprites_by_atlas[atlas_id],
            patched_ids,
            work_dir,
            patch_dir,
        )
        preview_path = work_dir / "atlases" / f"{atlas_id:03d}_repacked.png"
        rebuilt.save(preview_path)
        atlas_sizes[atlas_id] = (rebuilt.width, rebuilt.height)

        van_dds = dds_dir / f"{atlas_id:03d}.dds"
        if not van_dds.is_file():
            raise SystemExit(f"missing dds page: {van_dds}")
        if atlas_id in pages_to_compress:
            bbox = patched_sprites_bbox(sprites_by_atlas[atlas_id], patched_ids)
            print(
                f"compress atlas page {atlas_id:03d} ({rebuilt.width}x{rebuilt.height}) "
                f"bbox {bbox[0]},{bbox[1]}-{bbox[2]},{bbox[3]}"
            )
            compress_atlas_page(van_dds, rebuilt, bbox=bbox)

    g1t_archive = repack_g1t_archive(dds_dir)
    out_g1t = PACK00D1_PATCH_ROOT / base["g1t_pack_relpath"]
    out_g1t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(g1t_archive, out_g1t)
    print(f"wrote {out_g1t}")

    out_xml = PACK02_PATCH_ROOT / base["xml_pack_relpath"]
    atlases_for_uv = [
        {"id": atlas_id, "width": width, "height": height}
        for atlas_id, (width, height) in sorted(atlas_sizes.items())
    ]
    update_uis_xml_uvwh(xml_path, final_sprites, atlases_for_uv, out_xml)
    print(f"wrote {out_xml}")

    for uil_path in sorted(patch_dir.glob("uil_*.xml")):
        out_uil = PACK02_PATCH_ROOT / "saves" / "ui_en" / texture_stem / uil_path.name
        out_uil.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(uil_path, out_uil)
        print(f"wrote {out_uil}")


if __name__ == "__main__":
    main()
