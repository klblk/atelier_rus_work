#!/usr/bin/env python3
"""Build/install local tools: compress_bc3_region and gust_tools (pinned release).

By default skips work if binaries already exist. Use --force to rebuild/reinstall.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from rus_scripts_common import (
    BUILD_DIR,
    COMPRESS_BC3,
    GUST_EBM,
    GUST_G1T,
    GUST_PAK,
    ROOT,
)

# Bump this to pull a newer VitaSmith/gust_tools release tag.
GUST_TOOLS_VERSION = "v1.58"
GUST_TOOLS_ARCHIVE_URL = (
    f"https://github.com/VitaSmith/gust_tools/archive/refs/tags/{GUST_TOOLS_VERSION}.tar.gz"
)

COMPRESS_SRC = ROOT / "tools/compress_bc3_region_src"
GUST_TOOLS_DIR = ROOT / "tools/gust_tools"
INIT_TOOLS_WORK = BUILD_DIR / "init_tools"

GUST_BINARIES = (
    "gust_pak",
    "gust_elixir",
    "gust_g1t",
    "gust_enc",
    "gust_ebm",
    "gust_gmpk",
)
GUST_ENC_JSON = "gust_enc.json"


def _version_dirname(version: str) -> str:
    """GitHub tag archives unpack to gust_tools-<semver> (strip leading 'v')."""
    ver = version[1:] if version.startswith("v") else version
    return f"gust_tools-{ver}"


def required_tool_paths() -> list[Path]:
    return [
        COMPRESS_BC3,
        GUST_PAK,
        GUST_EBM,
        GUST_G1T,
        GUST_TOOLS_DIR / GUST_ENC_JSON,
    ]


def tools_ready() -> bool:
    return all(p.is_file() for p in required_tool_paths())


def require_cmds(*names: str) -> None:
    missing = [n for n in names if shutil.which(n) is None]
    if missing:
        raise SystemExit(f"missing required command(s): {', '.join(missing)}")


def build_compress_bc3() -> None:
    if not COMPRESS_SRC.is_dir():
        raise SystemExit(f"compress_bc3 sources not found: {COMPRESS_SRC}")
    if not (COMPRESS_SRC / "stb_dxt.h").is_file():
        raise SystemExit(f"stb_dxt.h missing in {COMPRESS_SRC} (should be in git)")
    print(f"Building compress_bc3_region from {COMPRESS_SRC}")
    subprocess.run(["make", "-C", str(COMPRESS_SRC)], check=True)
    if not COMPRESS_BC3.is_file():
        raise SystemExit(f"expected binary not created: {COMPRESS_BC3}")
    print(f"Installed: {COMPRESS_BC3}")


def download_gust_sources(*, force: bool) -> Path:
    INIT_TOOLS_WORK.mkdir(parents=True, exist_ok=True)
    archive_name = f"gust_tools-{GUST_TOOLS_VERSION}.tar.gz"
    archive_path = INIT_TOOLS_WORK / archive_name
    src_dir = INIT_TOOLS_WORK / _version_dirname(GUST_TOOLS_VERSION)

    if force and src_dir.exists():
        shutil.rmtree(src_dir)
    if force and archive_path.exists():
        archive_path.unlink()

    if not archive_path.is_file():
        print(f"Downloading {GUST_TOOLS_ARCHIVE_URL}")
        urllib.request.urlretrieve(GUST_TOOLS_ARCHIVE_URL, archive_path)

    if not src_dir.is_dir():
        print(f"Extracting {archive_path.name}")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(INIT_TOOLS_WORK)

    if not src_dir.is_dir():
        raise SystemExit(f"expected source dir after extract: {src_dir}")
    return src_dir


def build_and_install_gust(*, force: bool) -> None:
    src_dir = download_gust_sources(force=force)
    print(f"Building gust_tools {GUST_TOOLS_VERSION} in {src_dir}")
    subprocess.run(["make", "-C", str(src_dir)], check=True)

    GUST_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    for name in GUST_BINARIES:
        src = src_dir / name
        if not src.is_file():
            raise SystemExit(f"gust binary not built: {src}")
        dest = GUST_TOOLS_DIR / name
        shutil.copy2(src, dest)
        dest.chmod(dest.stat().st_mode | 0o111)
        print(f"Installed: {dest}")

    enc_json = src_dir / GUST_ENC_JSON
    if not enc_json.is_file():
        raise SystemExit(f"missing {GUST_ENC_JSON} in {src_dir}")
    shutil.copy2(enc_json, GUST_TOOLS_DIR / GUST_ENC_JSON)
    print(f"Installed: {GUST_TOOLS_DIR / GUST_ENC_JSON}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild/reinstall even if tools already exist",
    )
    args = parser.parse_args()

    if tools_ready() and not args.force:
        print("Tools already present — skip (use --force to rebuild)")
        for p in required_tool_paths():
            print(f"  {p}")
        return

    require_cmds("make", "cc")
    build_compress_bc3()
    build_and_install_gust(force=args.force)

    missing = [p for p in required_tool_paths() if not p.is_file()]
    if missing:
        items = "\n".join(f"- {p}" for p in missing)
        raise SystemExit(f"tools still missing after init:\n{items}")
    print("init_tools done")


if __name__ == "__main__":
    main()
