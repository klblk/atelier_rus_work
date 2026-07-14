"""PAK repack helpers: extract → work → patch overlay → gust_pak."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STRINGS_DIR = SCRIPTS_DIR / "strings"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(STRINGS_DIR) not in sys.path:
    sys.path.insert(0, str(STRINGS_DIR))

from rus_scripts_common import (  # noqa: E402
    BUILD_OUT_DATA_DIR,
    GUST_PAK,
    PACK00D1_EXTRACT,
    PACK00D1_PATCH_ROOT,
    PACK00D1_WORK,
    PACK01_EXTRACT,
    PACK01_PATCH_ROOT,
    PACK01_WORK,
    PACK02_EXTRACT,
    PACK02_PATCH_ROOT,
    PACK02_WORK,
    PACK_EXTRACTS_DIR,
    extract_dir_for,
)
from strings_common import load_gust_json  # noqa: E402

SUPPORTED_PACKS = ("PACK00D1", "PACK01", "PACK02")


@dataclass(frozen=True)
class PackLayout:
    pack: str
    extract_dir: Path
    patch_dir: Path
    work_dir: Path
    manifest_name: str
    out_pak: Path


def normalize_pack_name(arg: str) -> str:
    stem = Path(arg.strip()).stem.upper()
    if stem not in SUPPORTED_PACKS:
        supported = ", ".join(SUPPORTED_PACKS)
        raise ValueError(f"unsupported pack {arg!r}; expected one of: {supported}")
    return stem


def _default_patch_dir(pack: str) -> Path:
    return {
        "PACK00D1": PACK00D1_PATCH_ROOT,
        "PACK01": PACK01_PATCH_ROOT,
        "PACK02": PACK02_PATCH_ROOT,
    }[pack]


def _default_work_dir(pack: str) -> Path:
    return {
        "PACK00D1": PACK00D1_WORK,
        "PACK01": PACK01_WORK,
        "PACK02": PACK02_WORK,
    }[pack]


def pack_layout(
    pack: str,
    *,
    extracts_root: Path = PACK_EXTRACTS_DIR,
    patch_dir: Path | None = None,
    work_dir: Path | None = None,
    out_dir: Path = BUILD_OUT_DATA_DIR,
) -> PackLayout:
    pack = normalize_pack_name(pack)
    extract_dir = extract_dir_for(f"{pack}.PAK", extracts_root)
    return PackLayout(
        pack=pack,
        extract_dir=extract_dir,
        patch_dir=(patch_dir or _default_patch_dir(pack)).resolve(),
        work_dir=(work_dir or _default_work_dir(pack)).resolve(),
        manifest_name=f"{pack}.json",
        out_pak=(out_dir / f"{pack}.PAK").resolve(),
    )


def prepare_work_tree(extract_dir: Path, work_dir: Path) -> None:
    if not extract_dir.is_dir():
        raise FileNotFoundError(f"extract dir not found: {extract_dir}")
    shutil.rmtree(work_dir, ignore_errors=True)
    shutil.copytree(extract_dir, work_dir)


def overlay_patch(patch_dir: Path, work_dir: Path) -> int:
    if not patch_dir.is_dir():
        print(f"patch dir missing, skip overlay: {patch_dir}")
        return 0

    count = 0
    for src in sorted(patch_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(patch_dir)
        dst = work_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1

    if count == 0:
        print(f"patch dir empty, skip overlay: {patch_dir}")
    return count


def find_pack_json(work_dir: Path) -> Path:
    matches = sorted(work_dir.glob("PACK*.json"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected exactly one PACK*.json in {work_dir}, found {len(matches)}"
        )
    return matches[0]


def rebuild_pak(
    work_dir: Path,
    out_pak: Path,
    *,
    gust_pak: Path = GUST_PAK,
    json_path: Path | None = None,
) -> Path:
    work_dir = work_dir.resolve()
    json_path = (json_path or find_pack_json(work_dir)).resolve()
    if json_path.parent != work_dir:
        raise ValueError(f"json {json_path} must live under work dir {work_dir}")
    if not gust_pak.is_file():
        raise FileNotFoundError(f"gust_pak not found: {gust_pak}")

    subprocess.run([str(gust_pak), json_path.name], cwd=work_dir, check=True)
    pak_name = load_gust_json(json_path)["name"]
    built = work_dir / pak_name
    if not built.is_file():
        raise FileNotFoundError(f"gust_pak did not create {built}")

    out_pak = out_pak.resolve()
    out_pak.parent.mkdir(parents=True, exist_ok=True)
    if out_pak != built.resolve():
        out_pak.write_bytes(built.read_bytes())
    return out_pak


def repack_pack(
    pack: str,
    *,
    extracts_root: Path = PACK_EXTRACTS_DIR,
    patch_dir: Path | None = None,
    work_dir: Path | None = None,
    out_dir: Path = BUILD_OUT_DATA_DIR,
    gust_pak: Path = GUST_PAK,
    dry_run: bool = False,
) -> tuple[PackLayout, int, Path | None]:
    layout = pack_layout(
        pack,
        extracts_root=extracts_root,
        patch_dir=patch_dir,
        work_dir=work_dir,
        out_dir=out_dir,
    )

    if dry_run:
        overlay_count = sum(
            1 for path in layout.patch_dir.rglob("*") if path.is_file()
        ) if layout.patch_dir.is_dir() else 0
        print(f"[dry-run] pack={layout.pack}")
        print(f"[dry-run] extract -> work: {layout.extract_dir} -> {layout.work_dir}")
        print(f"[dry-run] overlay patch: {layout.patch_dir} ({overlay_count} files)")
        print(f"[dry-run] gust_pak {layout.manifest_name} -> {layout.out_pak}")
        return layout, overlay_count, None

    print(f"copy extract -> work: {layout.extract_dir}")
    prepare_work_tree(layout.extract_dir, layout.work_dir)

    print(f"overlay patch: {layout.patch_dir}")
    overlay_count = overlay_patch(layout.patch_dir, layout.work_dir)

    print(f"repack via gust_pak: {layout.manifest_name}")
    out_pak = rebuild_pak(layout.work_dir, layout.out_pak, gust_pak=gust_pak)
    return layout, overlay_count, out_pak
