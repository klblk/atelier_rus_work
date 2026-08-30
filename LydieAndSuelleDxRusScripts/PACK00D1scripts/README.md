# PACK00D1scripts

Скрипты для патча PACK00D1 (шрифт + UI-текстуры).

## Font (mainfont)

| Скрипт | Назначение |
|--------|------------|
| `unpack_g1t.py` | Распаковка vanilla mainfont .g1t → `build/g1t_work/` |
| `unpack_glyphs.py` | Экспорт глифов из mainfont |
| `pack_font_texture.py` | Сборка патченного mainfont → `build/PACK00D1_patch/` |

Подробнее: `exe_patches/phys_glyph/README.md`.

## UI texture (uis_gen .g1t)

| Скрипт | Назначение |
|--------|------------|
| `extract_g1t.py` | Распаковка UI .g1t → `build/extract_g1t/{texture}/` |
| `repack_g1t.py` | Сборка патча из `texture.json` + `PACK00D1scripts/{texture}/patch.json` |
| `patch_ui_textures.py` | Extract (если нужно) + repack для одной или нескольких текстур |
| `texture_repack_common.py` | Общие хелперы extract/repack |

### Extract

```bash
cd LydieAndSuelleDxRusScripts

# gen_styles UI (uis_gen_*.xml)
python3 PACK00D1scripts/extract_g1t.py \
  --g1t extracts/pack_extracts/PACK00D1_extract/data/x64/res_en/ui/a19_title.g1t

# etc/ UI: telop (pre-rendered narration strips)
python3 PACK00D1scripts/extract_g1t.py \
  --g1t extracts/pack_extracts/PACK00D1_extract/data/x64/res_en/ui/a19_telop_06.g1t

# etc/ UI: monster portrait (single full-page sprite)
python3 PACK00D1scripts/extract_g1t.py \
  --g1t extracts/pack_extracts/PACK00D1_extract/data/x64/res_en/ui/a19_monster_l_065.g1t

# no uis XML: full atlas page(s) only (e.g. ipu/*.g1t)
python3 PACK00D1scripts/extract_g1t.py \
  --g1t extracts/pack_extracts/PACK00D1_extract/data/x64/res_en/ipu/mm03_250_001.g1t
```

Выход: `build/extract_g1t/<stem>/` (`texture.json`, `atlases/`, `sprites/`, `source/`).

XML ищется в `saves/ui_en/` и `saves/ui/` (без `ui_tw`/`ui_sc`):

- `gen_styles/uis_gen_{stem}.xml` — обычные UI-текстуры
- `etc/uis_*.xml` — telop, monster portraits и др. (по ссылке на `{stem}.g1t`)

Если XML не найден, extract продолжается в режиме `atlas_only` (целая DDS-страница → один спрайт). Флаг `--require-xml` возвращает старое поведение (ошибка без XML).

Если PACK00D1 ещё не распакован: `python3 PACKutils_scripts/extract_packs.py --pack PACK00D1.PAK`.

### Repack

Патч и PNG для подмены лежат в `PACK00D1scripts/{texture}/` (рядом с `patch.json`).

```bash
python3 PACK00D1scripts/repack_g1t.py a19_title
```

| Выход | Путь |
|-------|------|
| .g1t | `build/PACK00D1_patch/data/x64/res_en/ui/{texture}.g1t` |
| uis_gen XML | `build/PACK02_patch/saves/ui_en/gen_styles/uis_gen_{texture}.xml` |
| uil layout XML | `build/PACK02_patch/saves/ui_en/{texture}/uil_*.xml` (если лежит рядом с `patch.json`) |
| Preview | `build/extract_g1t/{texture}/atlases/*_repacked.png` |

Финальная упаковка PAK: `python3 PACKutils_scripts/repack_pack.py PACK00D1` и `PACK02`.

### Orchestrator (несколько текстур)

```bash
python3 PACK00D1scripts/patch_ui_textures.py a19_title
python3 PACK00D1scripts/patch_ui_textures.py a19_title other_ui
python3 PACK00D1scripts/patch_ui_textures.py --all
```

Extract пропускается, если `build/extract_g1t/{texture}/` уже готов (`--force-extract` для пересоздания).

### build_translation

В `build_translation.ini`:

```ini
[packs]
ui_textures = a19_title
```

`build_translation.py` вызывает `patch_ui_textures.py` внутри блока PACK00D1 (между `pack_font_texture.py` и `repack_pack.py PACK00D1`).

`repack_g1t` пишет `uis_gen_*.xml` в `build/PACK02_patch/` — для попадания в игру нужен rebuild PACK02 (уже в полном pipeline `build_translation.py`).

Добавление новой текстуры: создать `PACK00D1scripts/{stem}/patch.json`, добавить `stem` в `ui_textures`.
