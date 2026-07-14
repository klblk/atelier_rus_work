"""PACK02 XML string patching helpers."""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_DIALOG_LIMIT_BYTES = 512
STRCOMBINEALL_NAME = "strcombineall.xml"
NPC_MESS_FILE_RE = re.compile(r"^str_npc_s\d+_mess\.xml$")
PACK02_STR_TAG_RE = re.compile(rb'<str(?: Text="([^"]*)")? String_No="(\d+)"\s*/>')


def npc_mess_file(name: str) -> bool:
    return bool(NPC_MESS_FILE_RE.match(name))


def pack02_string_pattern(string_no: str) -> bytes:
    return rb'<str Text="[^"]*" String_No="' + string_no.encode("ascii") + rb'"/>'


class Pack02XmlCache:
    """In-memory text_en XML cache; reads from source_dir, writes dirty files to out_dir."""

    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir
        self._data: dict[str, bytes] = {}
        self._dirty: set[str] = set()
        self._combine_index: dict[str, list[str]] | None = None
        self._layer_index: dict[str, dict[str, str]] = {}

    def get(self, rel_name: str) -> bytes:
        if rel_name not in self._data:
            path = self.source_dir / rel_name
            self._data[rel_name] = path.read_bytes()
        return self._data[rel_name]

    def set(self, rel_name: str, data: bytes) -> None:
        self._data[rel_name] = data
        self._dirty.add(rel_name)
        if rel_name == STRCOMBINEALL_NAME:
            self._combine_index = None
        elif rel_name in self._layer_index:
            del self._layer_index[rel_name]

    def flush(self, out_dir: Path) -> list[str]:
        flushed: list[str] = []
        out_dir.mkdir(parents=True, exist_ok=True)
        for rel_name in sorted(self._dirty):
            out_path = out_dir / rel_name
            out_path.write_bytes(self._data[rel_name])
            flushed.append(rel_name)
        self._dirty.clear()
        return flushed

    def _combine_texts(self, string_no: str) -> list[str]:
        if self._combine_index is None:
            self._combine_index = {}
            for match in PACK02_STR_TAG_RE.finditer(self.get(STRCOMBINEALL_NAME)):
                sn = match.group(2).decode("ascii")
                text = match.group(1).decode("utf-8", errors="replace") if match.group(1) else ""
                self._combine_index.setdefault(sn, []).append(text)
        return self._combine_index.get(string_no, [])

    def _layer_text(self, layer_file: str, string_no: str) -> str | None:
        if layer_file not in self._layer_index:
            index: dict[str, str] = {}
            for match in PACK02_STR_TAG_RE.finditer(self.get(layer_file)):
                index[match.group(2).decode("ascii")] = (
                    match.group(1).decode("utf-8", errors="replace") if match.group(1) else ""
                )
            self._layer_index[layer_file] = index
        return self._layer_index[layer_file].get(string_no)


def cached_match_text(
    cache: Pack02XmlCache, string_no: str, expected: str, layer_file: str
) -> bool:
    layer_text = cache._layer_text(layer_file, string_no)
    if layer_text != expected:
        return False
    combine_texts = cache._combine_texts(string_no)
    return bool(combine_texts) and all(text == expected for text in combine_texts)


def patch_cached(cache: Pack02XmlCache, rel_name: str, string_no: str, text: str) -> int:
    data = cache.get(rel_name)
    pattern = pack02_string_pattern(string_no)
    new_inner = text.encode("utf-8")
    replacement = b'<str Text="' + new_inner + b'" String_No="' + string_no.encode("ascii") + b'"/>'
    data2, count = re.subn(pattern, replacement, data)
    if count < 1:
        raise SystemExit(
            f"String_No={string_no} not found in {cache.source_dir / rel_name}"
        )
    cache.set(rel_name, data2)
    return count


def patch_catalog_cached(
    cache: Pack02XmlCache, string_no: str, text: str, layer_file: str
) -> None:
    patch_cached(cache, layer_file, string_no, text)
    patch_cached(cache, STRCOMBINEALL_NAME, string_no, text)
