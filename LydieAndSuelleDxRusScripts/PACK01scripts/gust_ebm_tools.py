"""Gust EBM JSON round-trip helpers for PACK01 scripts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import GUST_EBM  # noqa: E402

DEFAULT_EBM_LIMIT_BYTES = 800


def load_gust_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(
        r"\b0x([0-9a-fA-F]+)\b",
        lambda match: str(int(match.group(1), 16)),
        text,
    )
    return json.loads(text)


def dump_gust_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def rebuild_ebm_from_json(json_path: Path, gust_ebm: Path = GUST_EBM) -> Path:
    if not gust_ebm.is_file():
        raise FileNotFoundError(f"gust_ebm not found: {gust_ebm}")
    subprocess.run([str(gust_ebm), str(json_path)], check=True)
    name = load_gust_json(json_path)["name"]
    ebm_path = json_path.with_name(name)
    if not ebm_path.is_file():
        raise FileNotFoundError(f"gust_ebm did not create {ebm_path}")
    return ebm_path
