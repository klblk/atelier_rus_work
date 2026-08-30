"""Shared helpers for UI .g1t texture extract/repack."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

PACK00D1SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACK00D1SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    COMPRESS_BC3,
    EXTRACT_G1T_ROOT,
    GUST_G1T,
    PACK00D1_EXTRACT,
    PACK00D1_PATCH_ROOT,
    PACK02_EXTRACT,
    PACK02_PATCH_ROOT,
    ROOT,
)

DEFAULT_RESOLUTION_HD = 2160
ROOT_GROUP = "_root"
TEXTURE_JSON_NAME = "texture.json"

GEN_STYLES_DIRS = [
    PACK02_EXTRACT / "saves/ui_en/gen_styles",
    PACK02_EXTRACT / "saves/ui/gen_styles",
]

ETC_STYLES_DIRS = [
    PACK02_EXTRACT / "saves/ui_en/etc",
    PACK02_EXTRACT / "saves/ui/etc",
]


@dataclass
class SpriteDef:
    image_list: str
    image_name: str
    texture_index: int
    uv_x: int
    uv_y: int
    w: int
    h: int
    px_x: int = 0
    px_y: int = 0
    px_w: int = 0
    px_h: int = 0

    def sprite_png_rel(self) -> str:
        if self.image_list == ROOT_GROUP:
            return f"sprites/_root/{self.image_name}.png"
        return f"sprites/{self.image_list}/{self.image_name}.png"

    def pixel_box(self) -> tuple[int, int, int, int]:
        return (self.px_x, self.px_y, self.px_x + self.px_w, self.px_y + self.px_h)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.image_name,
            "image_list": self.image_list,
            "atlas": self.texture_index,
            "png": self.sprite_png_rel(),
            "x": self.px_x,
            "y": self.px_y,
            "w": self.px_w,
            "h": self.px_h,
        }


def texture_patch_dir(texture_stem: str) -> Path:
    return PACK00D1SCRIPTS_DIR / texture_stem


DEFAULT_UI_G1T_RELPATH = "data/x64/res_en/ui/{stem}.g1t"


def default_ui_g1t_path(stem: str) -> Path:
    return PACK00D1_EXTRACT / DEFAULT_UI_G1T_RELPATH.format(stem=stem)


def discover_patched_textures() -> list[str]:
    return sorted(
        p.name
        for p in PACK00D1SCRIPTS_DIR.iterdir()
        if p.is_dir() and (p / "patch.json").is_file()
    )


def extract_work_ready(stem: str) -> bool:
    work = EXTRACT_G1T_ROOT / stem
    return (work / TEXTURE_JSON_NAME).is_file() and (work / "source" / stem).is_dir()


def rel_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def pack_relpath(path: Path, pack_root: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(pack_root.resolve())).replace("\\", "/")
    except ValueError:
        return None


def read_uis_xml_text(xml_path: Path) -> str:
    raw = xml_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp932", errors="replace")


def uis_xml_search_dirs() -> list[Path]:
    return [*GEN_STYLES_DIRS, *ETC_STYLES_DIRS]


def find_uis_xml(g1t_path: Path) -> Path | None:
    stem = g1t_path.stem
    for styles_dir in GEN_STYLES_DIRS:
        candidate = styles_dir / f"uis_gen_{stem}.xml"
        if candidate.is_file():
            return candidate

    needle = f"{stem}.g1t"
    for styles_dir in uis_xml_search_dirs():
        if not styles_dir.is_dir():
            continue
        for xml_path in sorted(styles_dir.glob("uis*.xml")):
            if needle in read_uis_xml_text(xml_path):
                return xml_path
    return None


def texture_matches(texture_attr: str, g1t_name: str) -> bool:
    normalized = texture_attr.replace("\\", "/")
    return Path(normalized).name == g1t_name


def uv_to_pixel_box(
    uv_x: int,
    uv_y: int,
    w: int,
    h: int,
    page_width: int,
    resolution_tex: int,
) -> tuple[int, int, int, int]:
    scale = page_width / resolution_tex
    return (
        round(uv_x * scale),
        round(uv_y * scale),
        round(w * scale),
        round(h * scale),
    )


def pixel_to_uvwh(
    x: int,
    y: int,
    w: int,
    h: int,
    page_width: int,
    page_height: int,
) -> tuple[int, int, int, int]:
    resolution_tex_w = page_width * 2
    resolution_tex_h = page_height * 2
    return (
        round(x * resolution_tex_w / page_width),
        round(y * resolution_tex_h / page_height),
        round(w * resolution_tex_w / page_width),
        round(h * resolution_tex_h / page_height),
    )


def parse_uis_xml(xml_path: Path, g1t_name: str) -> tuple[int, list[SpriteDef]]:
    xml_text = read_uis_xml_text(xml_path)
    root = ET.fromstring(xml_text)
    resolution_hd = int(root.attrib.get("resolution_hd", DEFAULT_RESOLUTION_HD))
    sprites: list[SpriteDef] = []

    for image_list in root.findall("image_list"):
        list_name = image_list.attrib["name"]
        for image in image_list.findall("image"):
            texture = image.attrib.get("texture", "")
            if not texture_matches(texture, g1t_name):
                continue
            uv_x, uv_y, w, h = (int(v) for v in image.attrib["uvwh"].split(","))
            sprites.append(
                SpriteDef(
                    image_list=list_name,
                    image_name=image.attrib["name"],
                    texture_index=int(image.attrib["texture_index"]),
                    uv_x=uv_x,
                    uv_y=uv_y,
                    w=w,
                    h=h,
                )
            )

    for image in root.findall("image"):
        texture = image.attrib.get("texture", "")
        if not texture_matches(texture, g1t_name):
            continue
        uv_x, uv_y, w, h = (int(v) for v in image.attrib["uvwh"].split(","))
        sprites.append(
            SpriteDef(
                image_list=ROOT_GROUP,
                image_name=image.attrib["name"],
                texture_index=int(image.attrib["texture_index"]),
                uv_x=uv_x,
                uv_y=uv_y,
                w=w,
                h=h,
            )
        )

    return resolution_hd, sprites


def apply_pixel_coords(sprites: list[SpriteDef], pages: dict[int, Image.Image]) -> None:
    for sprite in sprites:
        page = pages[sprite.texture_index]
        resolution_tex = page.width * 2
        sprite.px_x, sprite.px_y, sprite.px_w, sprite.px_h = uv_to_pixel_box(
            sprite.uv_x,
            sprite.uv_y,
            sprite.w,
            sprite.h,
            page.width,
            resolution_tex,
        )


def unpack_g1t(g1t_path: Path, work_dir: Path) -> Path:
    if not GUST_G1T.is_file():
        raise FileNotFoundError(f"gust_g1t not found: {GUST_G1T}")

    source_dir = work_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    cached_g1t = source_dir / g1t_path.name
    shutil.copy2(g1t_path, cached_g1t)

    dds_dir = source_dir / g1t_path.stem
    dds_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(GUST_G1T), "-y", str(cached_g1t.name)], check=True, cwd=source_dir)
    return dds_dir


def load_dds_pages(dds_dir: Path) -> dict[int, Image.Image]:
    pages: dict[int, Image.Image] = {}
    for dds_path in sorted(dds_dir.glob("*.dds")):
        pages[int(dds_path.stem)] = Image.open(dds_path).convert("RGBA")
    if not pages:
        raise FileNotFoundError(f"No DDS pages in {dds_dir}")
    return pages


def save_atlas_pngs(pages: dict[int, Image.Image], work_dir: Path) -> list[dict[str, Any]]:
    atlas_dir = work_dir / "atlases"
    atlas_dir.mkdir(parents=True, exist_ok=True)
    atlases: list[dict[str, Any]] = []
    for index in sorted(pages):
        page = pages[index]
        rel = f"atlases/{index:03d}.png"
        page.save(work_dir / rel)
        atlases.append({"id": index, "png": rel, "width": page.width, "height": page.height})
    return atlases


def crop_and_save_sprites(
    sprites: list[SpriteDef],
    pages: dict[int, Image.Image],
    work_dir: Path,
) -> None:
    for sprite in sprites:
        page = pages[sprite.texture_index]
        out_path = work_dir / sprite.sprite_png_rel()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        page.crop(sprite.pixel_box()).save(out_path)


def sprites_from_full_pages(pages: dict[int, Image.Image], stem: str) -> list[SpriteDef]:
    sprites: list[SpriteDef] = []
    multi_page = len(pages) > 1
    for index in sorted(pages):
        page = pages[index]
        w, h = page.size
        image_name = f"{stem}__page{index:03d}" if multi_page else stem
        sprites.append(
            SpriteDef(
                image_list=ROOT_GROUP,
                image_name=image_name,
                texture_index=index,
                uv_x=0,
                uv_y=0,
                w=w,
                h=h,
                px_x=0,
                px_y=0,
                px_w=w,
                px_h=h,
            )
        )
    return sprites


def write_texture_json(
    *,
    work_dir: Path,
    g1t_path: Path,
    xml_path: Path | None,
    resolution_hd: int,
    atlases: list[dict[str, Any]],
    sprites: list[SpriteDef],
    mode: str = "uis_xml",
) -> Path:
    g1t_pack_relpath = pack_relpath(g1t_path, PACK00D1_EXTRACT)
    if g1t_pack_relpath is None:
        raise SystemExit(f"g1t not under PACK00D1 extract: {g1t_path}")

    payload: dict[str, Any] = {
        "version": 1,
        "mode": mode,
        "g1t": rel_to_root(g1t_path),
        "g1t_pack_relpath": g1t_pack_relpath,
        "resolution_hd": resolution_hd,
        "work_dir": rel_to_root(work_dir),
        "atlases": atlases,
        "sprites": [sprite.to_json() for sprite in sprites],
    }
    if xml_path is not None:
        xml_pack_relpath = pack_relpath(xml_path, PACK02_EXTRACT)
        if xml_pack_relpath is None:
            raise SystemExit(f"xml not under PACK02 extract: {xml_path}")
        payload["xml"] = rel_to_root(xml_path)
        payload["xml_pack_relpath"] = xml_pack_relpath
    else:
        payload["xml"] = None
        payload["xml_pack_relpath"] = None
    out_path = work_dir / TEXTURE_JSON_NAME
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def load_texture_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"unsupported texture.json version: {data.get('version')}")
    return data


def resolve_work_path(work_dir: Path, rel: str) -> Path:
    rel_path = Path(rel)
    if rel_path.is_absolute():
        return rel_path.resolve()
    return (work_dir / rel_path).resolve()


def resolve_sprite_png(work_dir: Path, patch_dir: Path | None, rel: str) -> Path:
    rel_path = Path(rel)
    if rel_path.is_absolute():
        path = rel_path.resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"sprite png not found: {rel}")

    if patch_dir is not None:
        candidate = (patch_dir / rel_path).resolve()
        if candidate.is_file():
            return candidate

    candidate = (work_dir / rel_path).resolve()
    if candidate.is_file():
        return candidate

    raise FileNotFoundError(f"sprite png not found: {rel}")


def merge_sprite(
    base: dict[str, Any],
    patch: dict[str, Any],
    work_dir: Path,
    patch_dir: Path | None = None,
) -> dict[str, Any]:
    merged = dict(base)
    for key in ("png", "x", "y", "w", "h", "atlas"):
        if key in patch:
            merged[key] = patch[key]

    if "png" in patch and ("w" not in patch or "h" not in patch):
        png_path = resolve_sprite_png(work_dir, patch_dir, patch["png"])
        with Image.open(png_path) as img:
            w, h = img.size
        if "w" not in patch:
            merged["w"] = w
        if "h" not in patch:
            merged["h"] = h
    return merged


def merge_sprites(
    base_sprites: list[dict[str, Any]],
    patch_sprites: list[dict[str, Any]],
    work_dir: Path,
    patch_dir: Path | None = None,
) -> list[dict[str, Any]]:
    by_id = {sprite["id"]: dict(sprite) for sprite in base_sprites}
    for patch in patch_sprites:
        sprite_id = patch.get("id")
        if not sprite_id:
            raise ValueError("patch sprite missing id")
        if sprite_id not in by_id:
            raise KeyError(f"unknown sprite id in patch: {sprite_id}")
        by_id[sprite_id] = merge_sprite(by_id[sprite_id], patch, work_dir, patch_dir)
    return list(by_id.values())


def rebuild_atlas_page(
    vanilla_path: Path,
    base_sprites: list[dict[str, Any]],
    final_sprites: list[dict[str, Any]],
    patched_ids: set[str],
    work_dir: Path,
    patch_dir: Path | None = None,
) -> Image.Image:
    atlas = Image.open(vanilla_path).convert("RGBA")

    for sprite in base_sprites:
        if sprite["id"] not in patched_ids:
            continue
        x = int(sprite["x"])
        y = int(sprite["y"])
        w = int(sprite["w"])
        h = int(sprite["h"])
        clear = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        atlas.paste(clear, (x, y))

    for sprite in final_sprites:
        png_path = resolve_sprite_png(work_dir, patch_dir, sprite["png"])
        img = Image.open(png_path).convert("RGBA")
        x = int(sprite["x"])
        y = int(sprite["y"])
        w = int(sprite["w"])
        h = int(sprite["h"])
        if img.size != (w, h):
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        if x + w > atlas.width or y + h > atlas.height:
            raise ValueError(
                f"sprite {sprite['id']} out of atlas bounds: "
                f"({x},{y})+({w},{h}) vs {atlas.size}"
            )
        atlas.paste(img, (x, y))
    return atlas


def patched_sprites_bbox(
    sprites: list[dict[str, Any]],
    patched_ids: set[str],
) -> tuple[int, int, int, int]:
    patched = [sprite for sprite in sprites if sprite["id"] in patched_ids]
    if not patched:
        raise ValueError("patched_sprites_bbox requires at least one patched sprite")
    x0 = min(int(sprite["x"]) for sprite in patched)
    y0 = min(int(sprite["y"]) for sprite in patched)
    x1 = max(int(sprite["x"]) + int(sprite["w"]) for sprite in patched)
    y1 = max(int(sprite["y"]) + int(sprite["h"]) for sprite in patched)
    return x0, y0, x1, y1


def compress_atlas_page(
    van_dds: Path,
    atlas: Image.Image,
    *,
    bbox: tuple[int, int, int, int] | None = None,
    compressor: Path = COMPRESS_BC3,
) -> None:
    if not compressor.is_file():
        raise FileNotFoundError(
            f"compress_bc3 not found: {compressor}\n"
            "Build: make -C tools/compress_bc3_region_src"
        )
    w, h = atlas.size
    if bbox is None:
        x0, y0, x1, y1 = 0, 0, w, h
    else:
        x0, y0, x1, y1 = bbox
    rgba_path = van_dds.with_suffix(".rgba")
    patched_dds = van_dds.with_name(van_dds.stem + "_patched.dds")
    rgba_path.write_bytes(atlas.tobytes())
    subprocess.run(
        [
            str(compressor),
            str(van_dds),
            str(patched_dds),
            str(rgba_path),
            str(w),
            str(h),
            str(x0),
            str(y0),
            str(x1),
            str(y1),
        ],
        check=True,
    )
    shutil.copy2(patched_dds, van_dds)
    rgba_path.unlink(missing_ok=True)
    patched_dds.unlink(missing_ok=True)


def repack_g1t_archive(dds_dir: Path) -> Path:
    if not GUST_G1T.is_file():
        raise FileNotFoundError(f"gust_g1t not found: {GUST_G1T}")
    archive = dds_dir.parent / f"{dds_dir.name}.g1t"
    subprocess.run([str(GUST_G1T), dds_dir.name], check=True, cwd=dds_dir.parent)
    if not archive.is_file():
        raise FileNotFoundError(f"gust_g1t did not create {archive}")
    return archive


def update_uis_xml_uvwh(
    xml_path: Path,
    sprites: list[dict[str, Any]],
    atlases: list[dict[str, Any]],
    out_path: Path,
) -> None:
    atlas_sizes = {int(item["id"]): (int(item["width"]), int(item["height"])) for item in atlases}
    uv_by_id: dict[str, str] = {}
    for sprite in sprites:
        atlas_id = int(sprite["atlas"])
        page_w, page_h = atlas_sizes[atlas_id]
        uv_x, uv_y, uv_w, uv_h = pixel_to_uvwh(
            int(sprite["x"]),
            int(sprite["y"]),
            int(sprite["w"]),
            int(sprite["h"]),
            page_w,
            page_h,
        )
        uv_by_id[sprite["id"]] = f"{uv_x},{uv_y},{uv_w},{uv_h}"

    text = xml_path.read_bytes().decode("cp932", errors="replace")
    for sprite_id, uvwh in uv_by_id.items():
        pattern = rf'(name="{re.escape(sprite_id)}"[^>]*uvwh=")[^"]*(")'
        repl = rf"\g<1>{uvwh}\2"
        new_text, count = re.subn(pattern, repl, text, count=1)
        if count != 1:
            raise KeyError(f"sprite not found in xml: {sprite_id}")
        text = new_text

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(text.encode("cp932", errors="replace"))
