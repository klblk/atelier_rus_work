# PACKutils_scripts

Общие утилиты для `PACK01scripts/`, `PACK02scripts/` и упаковки PAK.

| Модуль | Назначение |
|--------|------------|
| `encode_modes.py` | `EncodeMode` (`translated` / `full` / `none`), `resolve_output_text()` |
| `catalog.py` | `load_catalog()`, `group_pack01_entries()`, `group_pack02_entries()` |
| `text_encoder.py` | `make_encode_fn()` через `exe_patches/phys_glyph/encode_text.py`, `utf8_byte_length()` |
| `pak_repack.py` | `prepare_work_tree()`, `overlay_patch()`, `rebuild_pak()`, `repack_pack()` |
| `repack_pack.py` | CLI упаковки PACK00D1 / PACK01 / PACK02 |
| `extract_packs.py` | Extract PACK00D1 / PACK01 / PACK02 из game Data через gust_pak |

Не импортирует `work/scripts/`.

## Extract PAK

```bash
cd LydieAndSuelleDxRusScripts

python3 PACKutils_scripts/extract_packs.py
python3 PACKutils_scripts/extract_packs.py --pack PACK02.PAK --force
```

Выход: `extracts/pack_extracts/PACK*_extract/`. Также вызывается из `init.py`.

## Repack PAK

```bash
cd LydieAndSuelleDxRusScripts

# Полный pipeline (пример PACK01)
python3 PACK01scripts/encode_event_ebm.py
python3 PACKutils_scripts/repack_pack.py PACK01
# → build/out/Data/PACK01.PAK

python3 PACK02scripts/encode_text_en.py
python3 PACKutils_scripts/repack_pack.py PACK02

# Кастомный patch tree
python3 PACKutils_scripts/repack_pack.py PACK01 --patch-dir /tmp/my_pack01_patch

# Dry-run
python3 PACKutils_scripts/repack_pack.py PACK02 --dry-run
```

Шаги: `extracts/pack_extracts/PACK*_extract` → `build/PACK*_work` (fresh copytree) → overlay `build/PACK*_patch` → `gust_pak` → `build/out/Data/PACK*.PAK`.

| Аргумент | Default |
|----------|---------|
| `pack` | `PACK01` / `PACK02` / `PACK00D1` |
| `--patch-dir` | `build/PACK*_patch` |
| `--extracts-root` | `extracts/pack_extracts` |
| `--out-dir` | `build/out/Data` |
| `--dry-run` | только лог |
