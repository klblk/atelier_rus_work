"""Shared paths for LydieAndSuelleDxRusScripts release pipeline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
BUILD_DIR = SCRIPTS_DIR / "build"
BUILD_OUT_DATA_DIR = BUILD_DIR / "out/Data"
EXTRACTS_DIR = SCRIPTS_DIR / "extracts"
PACK_EXTRACTS_DIR = EXTRACTS_DIR / "pack_extracts"

DEFAULT_GAME_DIR = ROOT / "AtelierLydieAndSuelleDX"
DEFAULT_GAME_DATA_DIR = DEFAULT_GAME_DIR / "Data"

STEAMLESS_DIR = SCRIPTS_DIR / "steamless"
DEFAULT_STEAMLESS_EXE = ROOT / "steamless/Atelier_Lydie_and_Suelle_DX.exe.unpacked.exe"
STEAMLESS_DEST_EXE = STEAMLESS_DIR / DEFAULT_STEAMLESS_EXE.name
GUST_PAK = ROOT / "tools/gust_tools/gust_pak"
GUST_EBM = ROOT / "tools/gust_tools/gust_ebm"
GUST_G1T = ROOT / "tools/gust_tools/gust_g1t"
COMPRESS_BC3 = ROOT / "tools/compress_bc3_region"

PACKS_TO_EXTRACT = ("PACK00D1.PAK", "PACK01.PAK", "PACK02.PAK")

PACK00D1_EXTRACT = PACK_EXTRACTS_DIR / "PACK00D1_extract"
PACK00D1_VANILLA_MAINFONT_G1T = (
    PACK00D1_EXTRACT / "data/x64/res_en/font/mainfont_hd1080_x64_0.g1t"
)
PACK00D1_PATCH_ROOT = BUILD_DIR / "PACK00D1_patch"
PACK00D1_WORK = BUILD_DIR / "PACK00D1_work"
PACK00D1_PATCHED_MAINFONT_G1T = (
    PACK00D1_PATCH_ROOT / "data/x64/res_en/font/mainfont_hd1080_x64_0.g1t"
)
ATLAS_TABLE_CSV = BUILD_DIR / "atlas_table.csv"
UNPACK_GLYPHS_DIR = BUILD_DIR / "unpack_glyphs"
MAINFONT_PACK_WORK_DIR = BUILD_DIR / "mainfont_pack_work"
DEFAULT_G1T_WORK = BUILD_DIR / "g1t_work"
EXTRACT_G1T_ROOT = BUILD_DIR / "extract_g1t"

EXE_PATCHES_DIR = SCRIPTS_DIR / "exe_patches"
EXE_BUILD_DIR = BUILD_DIR / "exe"
BUILD_OUT_DIR = BUILD_DIR / "out"
PATCHED_EXE = BUILD_OUT_DIR / "Atelier_Lydie_and_Suelle_DX.exe"
PHYS_GLYPH_JSON_DIR = EXE_BUILD_DIR / "phys_glyph"
LENGTH_PATCHES_DIR = EXE_BUILD_DIR / "length_patches"
EBM_LENGTH_PATCHES_JSON = LENGTH_PATCHES_DIR / "ebm_length_patches.json"
DIALOG_LENGTH_PATCHES_JSON = LENGTH_PATCHES_DIR / "dialog_length_patches.json"
RECIPE_UI_COPY_LIMIT_PATCHES_JSON = LENGTH_PATCHES_DIR / "recipe_ui_copy_limit_patches.json"
QUEST_ETC_COPY_LIMIT_PATCHES_JSON = LENGTH_PATCHES_DIR / "quest_etc_copy_limit_patches.json"
PATCH_CHAIN_WORK_EXE = EXE_BUILD_DIR / ".patch_chain_work.exe"

PACK01_EXTRACT = PACK_EXTRACTS_DIR / "PACK01_extract"
PACK01_EVENT_EN = PACK01_EXTRACT / "event/event_en"
PACK01_EVENT_EBM_EXTRACT = EXTRACTS_DIR / "PACK01_event_ebm_extract"
PACK01_PATCH_ROOT = BUILD_DIR / "PACK01_patch"
PACK01_WORK = BUILD_DIR / "PACK01_work"

PACK02_EXTRACT = PACK_EXTRACTS_DIR / "PACK02_extract"
PACK02_TEXT_EN = PACK02_EXTRACT / "saves/text_en"
PACK02_UI_EN = PACK02_EXTRACT / "saves/ui_en"
PACK02_PATCH_ROOT = BUILD_DIR / "PACK02_patch"
PACK02_UI_PATCH = PACK02_PATCH_ROOT / "saves/ui_en"
PACK02_WORK = BUILD_DIR / "PACK02_work"

PACK02SCRIPTS_DIR = SCRIPTS_DIR / "PACK02scripts"
UI_STRINGS_JSON = PACK02SCRIPTS_DIR / "ui_strings.json"
UI_STRING_ID_MAP_JSON = PACK02SCRIPTS_DIR / "ui_string_id_map.json"

STRINGS_JSON = SCRIPTS_DIR / "strings/debug/strings.json"

EBM_GLOB = "event_message_*.ebm"


def extract_dir_for(pak_name: str, extracts_root: Path = PACK_EXTRACTS_DIR) -> Path:
    return extracts_root / f"{Path(pak_name).stem}_extract"
