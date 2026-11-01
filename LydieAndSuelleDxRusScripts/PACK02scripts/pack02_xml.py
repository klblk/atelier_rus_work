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


def format_str_tag(string_no: str, text: str) -> bytes:
    """Same tag shape as historical patch_cached replacement."""
    return (
        b'<str Text="'
        + text.encode("utf-8")
        + b'" String_No="'
        + string_no.encode("ascii")
        + b'"/>'
    )


class Pack02XmlCache:
    """In-memory text_en XML cache; reads from source_dir, writes dirty files to out_dir."""

    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir
        self._data: dict[str, bytes] = {}
        self._dirty: set[str] = set()
        # Per-file: string_no -> text (layer: one value; combine: last write still list via _texts_list)
        self._texts: dict[str, dict[str, list[str]]] = {}
        self._spans: dict[str, dict[str, list[tuple[int, int]]]] = {}

    def get(self, rel_name: str) -> bytes:
        if rel_name not in self._data:
            path = self.source_dir / rel_name
            self._data[rel_name] = path.read_bytes()
        return self._data[rel_name]

    def set(self, rel_name: str, data: bytes) -> None:
        self._data[rel_name] = data
        self._dirty.add(rel_name)
        self._reindex_file(rel_name)

    def flush(self, out_dir: Path) -> list[str]:
        flushed: list[str] = []
        out_dir.mkdir(parents=True, exist_ok=True)
        for rel_name in sorted(self._dirty):
            out_path = out_dir / rel_name
            out_path.write_bytes(self._data[rel_name])
            flushed.append(rel_name)
        self._dirty.clear()
        return flushed

    def _reindex_file(self, rel_name: str) -> None:
        texts: dict[str, list[str]] = {}
        spans: dict[str, list[tuple[int, int]]] = {}
        data = self.get(rel_name)
        for match in PACK02_STR_TAG_RE.finditer(data):
            sn = match.group(2).decode("ascii")
            text = match.group(1).decode("utf-8", errors="replace") if match.group(1) else ""
            texts.setdefault(sn, []).append(text)
            spans.setdefault(sn, []).append((match.start(), match.end()))
        self._texts[rel_name] = texts
        self._spans[rel_name] = spans

    def _ensure_index(self, rel_name: str) -> None:
        if rel_name not in self._texts:
            self._reindex_file(rel_name)

    def _combine_texts(self, string_no: str) -> list[str]:
        self._ensure_index(STRCOMBINEALL_NAME)
        return self._texts[STRCOMBINEALL_NAME].get(string_no, [])

    def _layer_text(self, layer_file: str, string_no: str) -> str | None:
        self._ensure_index(layer_file)
        values = self._texts[layer_file].get(string_no)
        if not values:
            return None
        return values[-1]

    def apply_file_updates(self, rel_name: str, updates: dict[str, str]) -> int:
        """Apply many string_no→text updates to one file in a single rebuild pass.

        Returns number of tag occurrences replaced.
        """
        if not updates:
            return 0
        self._ensure_index(rel_name)
        data = self.get(rel_name)
        spans_map = self._spans[rel_name]
        replacements: list[tuple[int, int, bytes]] = []
        replaced = 0
        for string_no, text in updates.items():
            tag_spans = spans_map.get(string_no)
            if not tag_spans:
                raise SystemExit(
                    f"String_No={string_no} not found in {self.source_dir / rel_name}"
                )
            new_tag = format_str_tag(string_no, text)
            for start, end in tag_spans:
                replacements.append((start, end, new_tag))
                replaced += 1
        replacements.sort(key=lambda item: item[0])
        parts: list[bytes] = []
        pos = 0
        for start, end, new_tag in replacements:
            if start < pos:
                raise SystemExit(f"overlapping str tags in {rel_name}")
            parts.append(data[pos:start])
            parts.append(new_tag)
            pos = end
        parts.append(data[pos:])
        self.set(rel_name, b"".join(parts))
        return replaced


def cached_match_text(
    cache: Pack02XmlCache, string_no: str, expected: str, layer_file: str
) -> bool:
    layer_text = cache._layer_text(layer_file, string_no)
    if layer_text != expected:
        return False
    combine_texts = cache._combine_texts(string_no)
    return bool(combine_texts) and all(text == expected for text in combine_texts)


def patch_cached(cache: Pack02XmlCache, rel_name: str, string_no: str, text: str) -> int:
    """Single-string patch (compat); prefer apply_updates for bulk encode."""
    return cache.apply_file_updates(rel_name, {string_no: text})


def patch_catalog_cached(
    cache: Pack02XmlCache, string_no: str, text: str, layer_file: str
) -> None:
    patch_cached(cache, layer_file, string_no, text)
    patch_cached(cache, STRCOMBINEALL_NAME, string_no, text)


def apply_updates(
    cache: Pack02XmlCache, updates: list[tuple[str, str, str]]
) -> None:
    """Apply collected (layer_file, string_no, text) updates in batch per file."""
    by_file: dict[str, dict[str, str]] = {}
    for layer_file, string_no, text in updates:
        by_file.setdefault(layer_file, {})[string_no] = text
        by_file.setdefault(STRCOMBINEALL_NAME, {})[string_no] = text
    for rel_name, file_updates in by_file.items():
        cache.apply_file_updates(rel_name, file_updates)
