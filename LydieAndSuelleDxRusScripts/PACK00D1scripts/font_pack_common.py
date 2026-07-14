"""Shared paths and layout helpers for PACK00D1 font scripts."""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

PACK00D1SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACK00D1SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    ATLAS_TABLE_CSV,
    BUILD_DIR,
    COMPRESS_BC3,
    DEFAULT_G1T_WORK,
    GUST_G1T,
    MAINFONT_PACK_WORK_DIR,
    PACK00D1_PATCHED_MAINFONT_G1T,
    PACK00D1_VANILLA_MAINFONT_G1T,
    ROOT,
    UNPACK_GLYPHS_DIR,
)

GLYPHS_DIR = PACK00D1SCRIPTS_DIR / "glyphs"
DEFAULT_ATLAS_TABLE = ATLAS_TABLE_CSV
DEFAULT_TEXTURE_G1T = PACK00D1_PATCHED_MAINFONT_G1T
VANILLA_G1T = PACK00D1_VANILLA_MAINFONT_G1T
VANILLA_G1T_SIZE = 8_388_664

DEFAULT_G1T_ARCHIVE = BUILD_DIR / "g1t_work.g1t"

UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
EXTRA = "«»≥"
TARGET_LETTERS = UPPER + LOWER + EXTRA

ATLAS_W = 4096
ATLAS_H = 2048
PADDING = 2
DEFAULT_START_X = 0
DEFAULT_START_Y = 1150

_FILENAME_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def case_for_letter(letter: str) -> str:
    if letter in UPPER:
        return "upper"
    if letter in LOWER:
        return "lower"
    if letter in EXTRA:
        return "extra"
    raise ValueError(f"unknown letter: {letter!r}")


def glyph_filename(letter: str, num: int) -> str:
    code = f"{ord(letter):04X}"
    if letter and not _FILENAME_FORBIDDEN.search(letter):
        return f"{num:03d}_{code}_{letter}.png"
    return f"{num:03d}_{code}.png"


def glyph_path_for(letter: str, num: int, glyphs_dir: Path = GLYPHS_DIR) -> Path:
    path = glyphs_dir / glyph_filename(letter, num)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def layout_block(
    glyphs: list[dict],
    start_x: int,
    start_y: int,
) -> tuple[list[dict], int]:
    """Place glyphs left-to-right with wrap; return placed list and next y."""
    placed: list[dict] = []
    x, y = start_x, start_y
    row_h = 0
    for g in glyphs:
        w, h = g["w"], g["h"]
        if x > start_x and x + w > ATLAS_W:
            x = start_x
            y += row_h + PADDING
            row_h = 0
        placed.append({**g, "x": x, "y": y, "w": w, "h": h})
        x += w + PADDING
        row_h = max(row_h, h)
    next_y = y + row_h + PADDING if placed else start_y
    return placed, next_y


def layout_rows(
    glyphs_by_case: dict[str, list[dict]],
    start_x: int = DEFAULT_START_X,
    start_y: int = DEFAULT_START_Y,
) -> list[dict]:
    """Assign x,y: upper block, lower block below, then extra."""
    placed: list[dict] = []
    y = start_y
    for case in ("upper", "lower", "extra"):
        block = glyphs_by_case.get(case, [])
        if not block:
            continue
        block_placed, y = layout_block(block, start_x, y)
        placed.extend(block_placed)
    return placed


def bbox_from_placed(placed: list[dict]) -> tuple[int, int, int, int]:
    min_x = min(g["x"] for g in placed)
    min_y = min(g["y"] for g in placed)
    max_x = max(g["x"] + g["w"] for g in placed)
    max_y = max(g["y"] + g["h"] for g in placed)
    return min_x, min_y, max_x, max_y


def glyphs_by_case_from_letters(
    letters: str = TARGET_LETTERS,
    glyphs_dir: Path = GLYPHS_DIR,
) -> dict[str, list[dict]]:
    from PIL import Image

    by_case: dict[str, list[dict]] = {"upper": [], "lower": [], "extra": []}
    for num, letter in enumerate(letters):
        png_path = glyph_path_for(letter, num, glyphs_dir)
        with Image.open(png_path) as im:
            w, h = im.size
        case = case_for_letter(letter)
        by_case[case].append(
            {
                "letter": letter,
                "num": num,
                "case": case,
                "png": png_path.name,
                "w": w,
                "h": h,
            }
        )
    return by_case


def g1t_work_dir_for(g1t_path: Path, out_dir: Path = BUILD_DIR) -> Path:
    return out_dir / f"{g1t_path.stem}_work"


def unpack_g1t_work(
    g1t_path: Path,
    out_work: Path,
    *,
    force: bool = False,
) -> Path:
    if not GUST_G1T.is_file():
        raise SystemExit(f"gust_g1t not found: {GUST_G1T}")
    if not g1t_path.is_file():
        raise SystemExit(f"g1t not found: {g1t_path}")

    out_parent = out_work.parent
    out_parent.mkdir(parents=True, exist_ok=True)
    archive = out_parent / f"{out_work.name}.g1t"

    if out_work.exists():
        if not force:
            if (out_work / "000.dds").is_file() and (out_work / "g1t.json").is_file():
                return out_work
            raise SystemExit(f"{out_work} exists; use --force to recreate")
        shutil.rmtree(out_work)
    if archive.exists():
        archive.unlink()

    shutil.copy2(g1t_path, archive)
    subprocess.run([str(GUST_G1T), "-y", archive.name], check=True, cwd=out_parent)

    if not (out_work / "000.dds").is_file():
        raise SystemExit(f"unpack failed: missing {out_work / '000.dds'}")
    if not (out_work / "g1t.json").is_file():
        raise SystemExit(f"unpack failed: missing {out_work / 'g1t.json'}")

    return out_work


def atlas_dds_from_g1t(
    g1t_path: Path,
    work_dir: Path | None = None,
    *,
    force: bool = False,
) -> Path:
    if work_dir is None:
        work_dir = g1t_work_dir_for(g1t_path)
    unpack_g1t_work(g1t_path.resolve(), work_dir.resolve(), force=force)
    return work_dir / "000.dds"


def load_atlas_table(path: Path) -> list[dict]:
    required = {"png", "w", "h", "x", "y", "letter"}
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise SystemExit(f"{path}: expected columns {sorted(required)}")
        for row in reader:
            png = (row.get("png") or "").strip()
            if not png:
                continue
            rows.append(
                {
                    "png": png,
                    "w": int(row["w"]),
                    "h": int(row["h"]),
                    "x": int(row["x"]),
                    "y": int(row["y"]),
                    "letter": (row.get("letter") or "").strip(),
                }
            )
    if not rows:
        raise SystemExit(f"{path}: no glyph rows")
    return rows
