#!/usr/bin/env python3
"""Build translation release: patch exe, encode packs, repack PAKs."""

from __future__ import annotations

import argparse
import configparser
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PACKUTILS_DIR = SCRIPTS_DIR / "PACKutils_scripts"
PHYS_GLYPH_DIR = SCRIPTS_DIR / "exe_patches/phys_glyph"
for path in (SCRIPTS_DIR, PACKUTILS_DIR, PHYS_GLYPH_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from encode_modes import EncodeMode  # noqa: E402
from phys_glyph_common import LETTER_CARRIER_MAP_RESOLVED_JSON  # noqa: E402
from rus_scripts_common import (  # noqa: E402
    BUILD_OUT_DATA_DIR,
    PATCHED_EXE,
    SCRIPTS_DIR as _SCRIPTS_DIR,
    STEAMLESS_DEST_EXE,
    STRINGS_JSON,
    UI_STRINGS_JSON,
)

DEFAULT_CONFIG = SCRIPTS_DIR / "build_translation.ini"

EBM_LIMIT_PATCHED = 800
EBM_LIMIT_VANILLA = 400
DIALOG_LIMIT_PATCHED = 512
DIALOG_LIMIT_VANILLA = 256

ENCODE_MODE_CHOICES = ("translated", "full", "none", "auto")


@dataclass(frozen=True)
class BuildSettings:
    strings_json: Path
    ui_strings_json: Path
    exe_in: Path
    exe_out: Path
    out_data_dir: Path
    phys_glyph: bool
    ebm_length: bool
    dialog_length: bool
    recipe_ui_copy_limit: bool
    quest_etc_copy_limit: bool
    rebuild_pack00d1: bool
    rebuild_pack01: bool
    rebuild_pack02: bool
    ui_textures: list[str]
    encode_mode: str
    dry_run: bool


def load_config(path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not path.is_file():
        raise SystemExit(f"config not found: {path}")
    cfg.read(path, encoding="utf-8")
    return cfg


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (_SCRIPTS_DIR / path).resolve()


def cfg_bool(cfg: configparser.ConfigParser, section: str, key: str, default: bool) -> bool:
    if not cfg.has_option(section, key):
        return default
    return cfg.getboolean(section, key)


def cfg_str(cfg: configparser.ConfigParser, section: str, key: str, default: str) -> str:
    if not cfg.has_option(section, key):
        return default
    return cfg.get(section, key).strip()


def pick(cli_val, ini_val, default):
    if cli_val is not None:
        return cli_val
    if ini_val is not None:
        return ini_val
    return default


def run_step(name: str, argv: list[str], *, cwd: Path) -> None:
    print(f"\n== {name} ==")
    print(" ".join(argv))
    subprocess.run(argv, cwd=cwd, check=True)


def resolve_encode_mode(
    mode: str,
    *,
    phys_glyph_applied: bool,
    resolved_path: Path,
) -> EncodeMode:
    if mode != "auto":
        return EncodeMode(mode)
    if not phys_glyph_applied:
        return EncodeMode.NONE
    if not resolved_path.is_file():
        raise SystemExit(
            f"letter carrier map not found: {resolved_path}\n"
            "Run phys_glyph patch first or set encode mode explicitly."
        )
    keys = json.loads(resolved_path.read_text(encoding="utf-8")).keys()
    has_latin = any(len(k) == 1 and k.isascii() and k.isalpha() for k in keys)
    return EncodeMode.FULL if has_latin else EncodeMode.TRANSLATED


def should_rebuild_pack(pack: str, *, rebuild: bool, out_data_dir: Path) -> bool:
    out_pak = out_data_dir / f"{pack}.PAK"
    if rebuild:
        return True
    if out_pak.is_file():
        print(f"\nSkip {pack} (exists: {out_pak})")
        return False
    return True


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_patch_exe(settings: BuildSettings) -> None:
    argv = [
        sys.executable,
        str(_SCRIPTS_DIR / "exe_patches/patch_exe.py"),
        "--exe-in",
        str(settings.exe_in),
        "--exe-out",
        str(settings.exe_out),
    ]
    argv.append("--phys-glyph" if settings.phys_glyph else "--no-phys-glyph")
    argv.append("--ebm-length" if settings.ebm_length else "--no-ebm-length")
    argv.append("--dialog-length" if settings.dialog_length else "--no-dialog-length")
    argv.append(
        "--recipe-ui-copy-limit" if settings.recipe_ui_copy_limit else "--no-recipe-ui-copy-limit"
    )
    argv.append(
        "--quest-etc-copy-limit" if settings.quest_etc_copy_limit else "--no-quest-etc-copy-limit"
    )
    run_step("exe_patches/patch_exe.py", argv, cwd=_SCRIPTS_DIR)


def run_pack00d1(settings: BuildSettings) -> None:
    argv = [sys.executable, str(_SCRIPTS_DIR / "PACK00D1scripts/pack_font_texture.py")]
    run_step("PACK00D1scripts/pack_font_texture.py", argv, cwd=_SCRIPTS_DIR)

    if settings.ui_textures:
        ui_patch = [
            sys.executable,
            str(_SCRIPTS_DIR / "PACK00D1scripts/patch_ui_textures.py"),
            *settings.ui_textures,
        ]
        if settings.dry_run:
            ui_patch.append("--dry-run")
        run_step("PACK00D1scripts/patch_ui_textures.py", ui_patch, cwd=_SCRIPTS_DIR)

    repack = [
        sys.executable,
        str(_SCRIPTS_DIR / "PACKutils_scripts/repack_pack.py"),
        "PACK00D1",
        "--out-dir",
        str(settings.out_data_dir),
    ]
    if settings.dry_run:
        repack.append("--dry-run")
    run_step("PACKutils_scripts/repack_pack.py PACK00D1", repack, cwd=_SCRIPTS_DIR)


def run_pack01(settings: BuildSettings, *, encode_mode: EncodeMode, ebm_limit_bytes: int) -> None:
    encode = [
        sys.executable,
        str(_SCRIPTS_DIR / "PACK01scripts/encode_event_ebm.py"),
        "--strings-json",
        str(settings.strings_json),
        "--mode",
        encode_mode.value,
        "--ebm-limit-bytes",
        str(ebm_limit_bytes),
    ]
    if settings.dry_run:
        encode.append("--dry-run")
    run_step("PACK01scripts/encode_event_ebm.py", encode, cwd=_SCRIPTS_DIR)

    repack = [
        sys.executable,
        str(_SCRIPTS_DIR / "PACKutils_scripts/repack_pack.py"),
        "PACK01",
        "--out-dir",
        str(settings.out_data_dir),
    ]
    if settings.dry_run:
        repack.append("--dry-run")
    run_step("PACKutils_scripts/repack_pack.py PACK01", repack, cwd=_SCRIPTS_DIR)


def run_pack02(
    settings: BuildSettings,
    *,
    encode_mode: EncodeMode,
    dialog_limit_bytes: int,
) -> None:
    encode = [
        sys.executable,
        str(_SCRIPTS_DIR / "PACK02scripts/encode_text_en.py"),
        "--strings-json",
        str(settings.strings_json),
        "--mode",
        encode_mode.value,
        "--dialog-limit-bytes",
        str(dialog_limit_bytes),
    ]
    if settings.dry_run:
        encode.append("--dry-run")
    run_step("PACK02scripts/encode_text_en.py", encode, cwd=_SCRIPTS_DIR)

    ui_patch = [
        sys.executable,
        str(_SCRIPTS_DIR / "PACK02scripts/patch_ui_strings.py"),
        "--strings-json",
        str(settings.strings_json),
        "--config",
        str(settings.ui_strings_json),
    ]
    if settings.dry_run:
        ui_patch.append("--dry-run")
    run_step("PACK02scripts/patch_ui_strings.py", ui_patch, cwd=_SCRIPTS_DIR)

    repack = [
        sys.executable,
        str(_SCRIPTS_DIR / "PACKutils_scripts/repack_pack.py"),
        "PACK02",
        "--out-dir",
        str(settings.out_data_dir),
    ]
    if settings.dry_run:
        repack.append("--dry-run")
    run_step("PACKutils_scripts/repack_pack.py PACK02", repack, cwd=_SCRIPTS_DIR)


def build_settings_from_args(args: argparse.Namespace) -> BuildSettings:
    config_path = args.config.resolve()
    cfg = load_config(config_path)

    def path_opt(cli: Path | None, section: str, key: str, default: Path) -> Path:
        ini_val = cfg_str(cfg, section, key, "") if cfg.has_option(section, key) else None
        ini_path = resolve_path(ini_val) if ini_val else None
        if cli is not None:
            return cli.resolve()
        if ini_path is not None:
            return ini_path
        return default.resolve()

    def bool_opt(cli: bool | None, section: str, key: str, default: bool) -> bool:
        ini_val = cfg_bool(cfg, section, key, default) if cfg.has_section(section) else default
        return pick(cli, ini_val, default)

    encode_mode = pick(
        args.encode_mode,
        cfg_str(cfg, "encode", "mode", "auto") if cfg.has_section("encode") else "auto",
        "auto",
    )
    if encode_mode not in ENCODE_MODE_CHOICES:
        raise SystemExit(f"invalid encode mode: {encode_mode!r}")

    if args.ui_textures is not None:
        ui_textures = parse_csv_list(args.ui_textures)
    elif cfg.has_option("packs", "ui_textures"):
        ui_textures = parse_csv_list(cfg_str(cfg, "packs", "ui_textures", ""))
    else:
        ui_textures = []

    return BuildSettings(
        strings_json=path_opt(args.strings_json, "paths", "strings_json", STRINGS_JSON),
        ui_strings_json=path_opt(
            args.ui_strings_json, "paths", "ui_strings_json", UI_STRINGS_JSON
        ),
        exe_in=path_opt(args.exe_in, "paths", "exe_in", STEAMLESS_DEST_EXE),
        exe_out=path_opt(args.exe_out, "paths", "exe_out", PATCHED_EXE),
        out_data_dir=path_opt(args.out_data_dir, "paths", "out_data_dir", BUILD_OUT_DATA_DIR),
        phys_glyph=bool_opt(args.phys_glyph, "exe", "phys_glyph", True),
        ebm_length=bool_opt(args.ebm_length, "exe", "ebm_length", True),
        dialog_length=bool_opt(args.dialog_length, "exe", "dialog_length", True),
        recipe_ui_copy_limit=bool_opt(
            args.recipe_ui_copy_limit, "exe", "recipe_ui_copy_limit", True
        ),
        quest_etc_copy_limit=bool_opt(
            args.quest_etc_copy_limit, "exe", "quest_etc_copy_limit", True
        ),
        rebuild_pack00d1=bool_opt(args.rebuild_PACK00D1, "packs", "rebuild_PACK00D1", True),
        rebuild_pack01=bool_opt(args.rebuild_PACK01, "packs", "rebuild_PACK01", True),
        rebuild_pack02=bool_opt(args.rebuild_PACK02, "packs", "rebuild_PACK02", True),
        ui_textures=ui_textures,
        encode_mode=encode_mode,
        dry_run=args.dry_run,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="INI config (default: build_translation.ini)",
    )
    parser.add_argument("--strings-json", type=Path, default=None)
    parser.add_argument("--ui-strings-json", type=Path, default=None)
    parser.add_argument("--exe-in", type=Path, default=None)
    parser.add_argument("--exe-out", type=Path, default=None)
    parser.add_argument("--out-data-dir", type=Path, default=None)
    parser.add_argument(
        "--phys-glyph",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--ebm-length",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--dialog-length",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--recipe-ui-copy-limit",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--quest-etc-copy-limit",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--rebuild-PACK00D1",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--rebuild-PACK01",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--rebuild-PACK02",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--ui-textures",
        default=None,
        help="comma-separated UI texture stems for PACK00D1 patch (overrides ini)",
    )
    parser.add_argument(
        "--encode-mode",
        choices=ENCODE_MODE_CHOICES,
        default=None,
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = build_settings_from_args(args)

    if (
        not settings.phys_glyph
        and not settings.ebm_length
        and not settings.dialog_length
        and not settings.recipe_ui_copy_limit
        and not settings.quest_etc_copy_limit
    ):
        raise SystemExit("no exe patches selected (all disabled)")

    if should_rebuild_pack(
        "PACK00D1", rebuild=settings.rebuild_pack00d1, out_data_dir=settings.out_data_dir
    ):
        run_pack00d1(settings)

    run_patch_exe(settings)

    encode_mode = resolve_encode_mode(
        settings.encode_mode,
        phys_glyph_applied=settings.phys_glyph,
        resolved_path=LETTER_CARRIER_MAP_RESOLVED_JSON.resolve(),
    )
    ebm_limit_bytes = EBM_LIMIT_PATCHED if settings.ebm_length else EBM_LIMIT_VANILLA
    dialog_limit_bytes = DIALOG_LIMIT_PATCHED if settings.dialog_length else DIALOG_LIMIT_VANILLA

    print("\n== encode settings ==")
    print(f"mode: {encode_mode.value} (config: {settings.encode_mode})")
    print(f"ebm_limit_bytes: {ebm_limit_bytes}")
    print(f"dialog_limit_bytes: {dialog_limit_bytes}")

    if should_rebuild_pack(
        "PACK01", rebuild=settings.rebuild_pack01, out_data_dir=settings.out_data_dir
    ):
        run_pack01(settings, encode_mode=encode_mode, ebm_limit_bytes=ebm_limit_bytes)

    if should_rebuild_pack(
        "PACK02", rebuild=settings.rebuild_pack02, out_data_dir=settings.out_data_dir
    ):
        run_pack02(
            settings,
            encode_mode=encode_mode,
            dialog_limit_bytes=dialog_limit_bytes,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
