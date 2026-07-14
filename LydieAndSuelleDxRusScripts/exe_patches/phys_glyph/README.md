# Phys glyph — патч физических блоков exe

Патч steamless-unpacked exe для отображения кириллицы через carrier-иероглифы.
Часть release-пайплайна `LydieAndSuelleDxRusScripts/`.

## Физический блок (28 байт @ `phys_block_off`)

Каждая запись в exe описывает один глиф в атласе шрифта:

```
+0 .. +3    code (uint32 LE, UTF-8 bytes reversed in low bytes)
+4 .. +11   rect (x, y, w, h — uint16 × 4)
+12 .. +15  tail (uint32)
+16 .. +27  metrics (m0..m5 — uint16 × 6)
```

Все смещения — **phys+** от `phys_block_off` (абсолютный offset записи в exe).

### Типы символов

**Short-code** — 1–2 байта UTF-8 в поле `code`: цифры, латиница, `«»≥`. Параметры читаются сканером из contiguous-таблицы в exe.

**Kanji pool** — 100 иероглифов (`KANJI_100` в [`kanji_carriers.py`](kanji_carriers.py)), production pool entries 0..99. Параметры тоже читаются из exe, но список символов задан заранее.

### Anchor и scan range

Сканер ищет digit `0` (`code=0x30`) и выбирает hit **ближайший к kanji region** (ниже ~`0xC236E8`). Ожидаемый anchor: `0xC1FF90` — начало contiguous digit/Latin table.

Scan range: `0xC1FF90`–`0xC30000`, stride 4 байта (по полю `code`).

## JSON-артефакты (`build/exe/phys_glyph/`)

| Файл | Описание |
|------|----------|
| `phys_block_map.json` | `{ letter: { code, x, y, w, h, m0, m1, m2, tail, phys_block_off } }` — vanilla exe |
| `phys_block_map.md` | краткая сводка scan (генерируется автоматически) |
| `virtual_phys_blocks.json` | виртуальные параметры кириллицы А–Я, а–я, `«»≥` (без `code`/`phys_block_off`) |
| `letter_carrier_map.json` | `{ cyrillic_letter: carrier_letter }` |
| `letter_carrier_map_resolved.json` | carrier map + rule-2 reloc pairs |

## Скрипты

| Скрипт | Назначение | Вход | Выход |
|--------|------------|------|-------|
| `scan_phys_block_map.py` | Скан vanilla exe → phys map | `--exe` (default steamless) | `phys_block_map.json` + `.md` |
| `build_virtual_phys_blocks.py` | Виртуальные блоки кириллицы | `build/atlas_table.csv` | `virtual_phys_blocks.json` |
| `build_letter_carrier_map.py` | Карта letter→carrier | virtual + phys maps | `letter_carrier_map.json` |
| `patch_phys_glyph_exe.py` | Патч exe | carrier + maps + exe-in | patched exe + resolved json |
| `encode_text.py` | Кодирование текста | текст / `--file` | stdout |

### Patch rules (`letter1` → `letter2`)

1. **Kanji carrier** (`letter2` ∈ `KANJI_100`): записать glyph params `letter1` в phys block `letter2` (поле `code` не меняется)
2. **Short-code carrier** (`letter2` в phys map, не kanji): stash оригинальные rect/metrics/tail `letter2` в первый свободный kanji; записать params `letter1` в `letter2`; resolved map дополняется `{letter2: free_kanji}`

Параметры `letter1` берутся из `virtual_phys_blocks.json`; если символа там нет — из `phys_block_map.json`.

## Команды

```bash
cd LydieAndSuelleDxRusScripts

# Полный патч: ebm_length → dialog_length → phys_glyph (все включены по умолчанию)
python3 exe_patches/patch_exe.py

# Идемпотентный skip
python3 exe_patches/patch_exe.py --skip

# Только length-патчи (без phys_glyph)
python3 exe_patches/patch_exe.py --no-phys-glyph

# Только phys_glyph (без length)
python3 exe_patches/patch_exe.py --no-ebm-length --no-dialog-length

# Отключить отдельные патчи
python3 exe_patches/patch_exe.py --no-ebm-length
python3 exe_patches/patch_exe.py --no-dialog-length

# Только phys_glyph standalone
python3 exe_patches/phys_glyph/patch_phys_glyph_exe.py

# Encode текста
python3 exe_patches/phys_glyph/encode_text.py "Тест «цитата»"
```

### Флаги `patch_exe.py`

| Флаг | Патч | Default |
|------|------|---------|
| `--phys-glyph` / `--no-phys-glyph` | phys_glyph subprocess | on |
| `--ebm-length` / `--no-ebm-length` | EBM buffer 400→800 B | on |
| `--dialog-length` / `--no-dialog-length` | dialog buffer 256→512 B | on |

Порядок применения: **EBM → dialog → phys_glyph**. Length JSON пишется в `build/exe/length_patches/`.

## Пути

| Роль | Путь |
|------|------|
| Вход exe | `steamless/Atelier_Lydie_and_Suelle_DX.exe.unpacked.exe` |
| Выход exe | `build/out/Atelier_Lydie_and_Suelle_DX.exe` |
| JSON | `build/exe/phys_glyph/` |
| Atlas prerequisite | `build/atlas_table.csv` (из `PACK00D1scripts/pack_font_texture.py`) |

## Prerequisite chain

Перед первым прогоном:

1. `init.py` — extracts
2. `PACK00D1scripts/pack_font_texture.py` — `build/atlas_table.csv`
3. steamless exe в `LydieAndSuelleDxRusScripts/steamless/`

`patch_phys_glyph_exe.py` автоматически вызывает `build_letter_carrier_map.py --fill-kanji --force`, который пересоздаёт prerequisite JSON.
