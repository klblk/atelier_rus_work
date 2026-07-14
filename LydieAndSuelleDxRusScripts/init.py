#!/usr/bin/env python3
"""Initialize LydieAndSuelleDxRusScripts pipeline.

Builds local tools, validates game files, optionally installs a Steamless-unpacked
exe, then runs:
- init_tools.py
- PACKutils_scripts/extract_packs.py
- PACK01scripts/extract_pack01_event_ebm.py
- strings/collect_strings.py
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from rus_scripts_common import (
    DEFAULT_GAME_DIR,
    DEFAULT_STEAMLESS_EXE,
    GUST_EBM,
    GUST_PAK,
    PACKS_TO_EXTRACT,
    STEAMLESS_DEST_EXE,
    STEAMLESS_DIR,
)

STEAMLESS_CLI_URL = "https://github.com/oureveryday/Steamless_CLI"


def validate_game_data(game_dir: Path) -> Path:
    game_dir = game_dir.resolve()
    if not game_dir.is_dir():
        raise SystemExit(f"game dir not found: {game_dir}")

    data_dir = (game_dir / "Data").resolve()
    if not data_dir.is_dir():
        raise SystemExit(f"game Data dir not found: {data_dir}")

    missing: list[Path] = []
    for name in PACKS_TO_EXTRACT:
        pak = data_dir / name
        if not pak.is_file():
            missing.append(pak)

    if missing:
        items = "\n".join(f"- {p}" for p in missing)
        raise SystemExit(f"missing required PAK files:\n{items}")

    return data_dir


def validate_tools() -> None:
    missing: list[Path] = []
    for tool in (GUST_PAK, GUST_EBM):
        if not tool.is_file():
            missing.append(tool)
    if missing:
        items = "\n".join(f"- {p}" for p in missing)
        raise SystemExit(f"missing required tools:\n{items}")


def install_steamless_exe(source: Path) -> bool:
    source = source.resolve()
    if not source.is_file():
        print(
            "WARNING: steamless-unpacked exe not found. "
            f"Provide --steamless-exe or unpack it using Steamless_CLI: {STEAMLESS_CLI_URL}"
        )
        return False

    STEAMLESS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, STEAMLESS_DEST_EXE)
    print(f"Installed steamless exe: {STEAMLESS_DEST_EXE}")
    return True


def run_step(name: str, argv: list[str], *, cwd: Path) -> None:
    print(f"\n== {name} ==")
    print(" ".join(argv))
    subprocess.run(argv, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=DEFAULT_GAME_DIR,
        help="Game install root directory (contains Data/)",
    )
    parser.add_argument(
        "--steamless-exe",
        type=Path,
        default=DEFAULT_STEAMLESS_EXE,
        help="Steamless-unpacked exe to copy into LydieAndSuelleDxRusScripts/steamless/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run extract and collection steps even if outputs exist",
    )
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent

    init_tools_argv = [sys.executable, str(scripts_dir / "init_tools.py")]
    if args.force:
        init_tools_argv.append("--force")
    run_step("init_tools.py", init_tools_argv, cwd=scripts_dir)

    validate_tools()
    data_dir = validate_game_data(args.game_dir)
    install_steamless_exe(args.steamless_exe)

    extract_packs = [
        sys.executable,
        str(scripts_dir / "PACKutils_scripts/extract_packs.py"),
        "--data-dir",
        str(data_dir),
    ]
    if args.force:
        extract_packs.append("--force")
    run_step("PACKutils_scripts/extract_packs.py", extract_packs, cwd=scripts_dir)

    extract_ebm = [sys.executable, str(scripts_dir / "PACK01scripts/extract_pack01_event_ebm.py")]
    if args.force:
        extract_ebm.append("--force")
    run_step("PACK01scripts/extract_pack01_event_ebm.py", extract_ebm, cwd=scripts_dir)

    collect_strings = [sys.executable, str(scripts_dir / "strings/collect_strings.py")]
    if args.force:
        collect_strings.extend(["--merge", "--force"])
    run_step("strings/collect_strings.py", collect_strings, cwd=scripts_dir)


if __name__ == "__main__":
    main()

