# a19_telop — manifest для перевода telop-текстур

Каталог для подготовки русских telop-полос (`etc_a19_telop_0000`–`0198`, 199 спрайтов в 17 атласах `a19_telop_01`–`17`).

## Файлы

| Файл | Назначение |
|------|------------|
| `sprites.json` | Каталог всех telop-спрайтов |
| `gradients.json` | Палитра градиентов заливки текста (шаблон) |

Источник имён и размеров: `extracts/pack_extracts/PACK02_extract/saves/ui_en/etc/uis_a19_telop.xml`.

Раскладка сцен (какие `image_no` показываются вместе): `extracts/pack_extracts/PACK02_extract/saves/ui_en/a19_telop/uil_a19_telop01.xml`.

## `sprites.json`

Каждый элемент массива `sprites`:

| Поле | Описание |
|------|----------|
| `index` | Номер 0–198 (`image_no` в `uil`) |
| `id` | Имя спрайта, напр. `etc_a19_telop_0070` |
| `g1t` | Атлас, напр. `a19_telop_06` |
| `w`, `h` | Размер полосы в пикселях (обычно 1536×96 или 1536×192 для title cards) |
| `text` | Текст для отрисовки (заполняется вручную) |
| `ebm` | Ссылка на строку EBM (заполняется вручную) |
| `gradient` | Ключ из `gradients.json` (заполняется вручную) |

По умолчанию `text`, `ebm` и `gradient` — пустые строки `""`.

### Формат `ebm`

```
ebm:mm01/event_message_mm01_070.ebm:0
```

Одна EBM-строка может давать несколько telop-спрайтов, если в `original` есть `<CR>` (две строки на экране). Исключения возможны: например, для `ebm:mm01/event_message_mm01_070.ebm:5` весь текст идёт в один telop, несмотря на `<CR>` в EBM.

### Размеры полос

- **1536×96** — обычная однострочная полоса (большинство спрайтов).
- **1536×192** — title cards (`172`–`181`, `186`–`187`, `198`).

### `a19_telop_14` (спрайты 182–185)

Ending-строки (не DX title cards). В `uil` используются в 3-sprite сценах вместе с соседними полосами:

| Сцена | Спрайты |
|-------|---------|
| `telop28` | 54, 55, **182** |
| `telop78` | 152, 153, **183** |
| `telop83` | 162, 163, **184** |
| `telop84` | 164, 165, **185** |

Градиенты у `182`–`185` часто совпадают с соседними спрайтами той же сцены.

## `gradients.json`

Шаблон с примерами `gradient1`, `gradient2`. Новые градиенты добавляются вручную:

```json
"gradientN": {
  "color1": "#ffffff",
  "color2": "#ffffff",
  "stroke": "#ffffff"
}
```

Цвета в формате `#rrggbb`.

## Генерация PNG

Требуется **ImageMagick** (`convert` в PATH) и шрифт `fonts/MarckScript-Regular.ttf` в корне репозитория.

Выход: `LydieAndSuelleDxRusScripts/build/a19_telops/`:

```
build/a19_telops/
  gradients/     # gradient1.png … gradient13.png
  sprites/       # etc_a19_telop_NNNN.png (только спрайты с непустым text)
```

### Команды

```bash
cd LydieAndSuelleDxRusScripts/PACK00D1scripts/a19_telops

# градиентные тайлы + спрайты
python3 generate_telops.py

# по отдельности
python3 generate_telop_gradients.py
python3 generate_telop_sprites.py
```

Опции: `--force` (перезапись), `--dry-run` (только команды), `--only-index N` (один спрайт, в `generate_telop_sprites.py` / `generate_telops.py`).

Генерируются **только** спрайты, у которых поле `text` не пустое.

### Repack в `.g1t`

UIS-координаты для всех telop-атласов лежат в **общем** [`uis_a19_telop.xml`](../../../extracts/pack_extracts/PACK02_extract/saves/ui_en/etc/uis_a19_telop.xml) (UTF-8 BOM), не в `uis_gen_a19_telop_XX.xml`.

Файлы `PACK00D1scripts/a19_telop_XX/patch.json` (01–17) уже лежат в репозитории — по одному на каждый атлас со спрайтами из `sprites.json`.

1. Разложить PNG по папкам атласов:

```bash
cd LydieAndSuelleDxRusScripts/PACK00D1scripts/a19_telops
python3 copy_telop_sprites.py
```

По умолчанию перезаписывает файлы в `PACK00D1scripts/a19_telop_XX/`. Опции: `--dry-run`, `--no-overwrite`, `--g1t a19_telop_06` (один атлас).

2. Repack одного атласа или всех:

```bash
cd LydieAndSuelleDxRusScripts/PACK00D1scripts
python3 repack_g1t.py a19_telop_01
python3 patch_ui_textures.py --all
```

Выход:
- `build/PACK00D1_patch/data/x64/res_en/ui/a19_telop_01.g1t`
- `build/PACK02_patch/saves/ui_en/etc/uis_a19_telop.xml` (обновляются `uvwh` только для спрайтов текущего атласа)

Для полной сборки добавьте stem в [`build_translation.ini`](../../build_translation.ini) (`ui_textures`); `build_translation.py` вызовет `patch_ui_textures.py` (extract → repack).

При repack нескольких telop-атlasов подряд repack читает уже пропатченный `uis_a19_telop.xml` из `build/PACK02_patch/`, если он существует.

### Градиентные тайлы

Для каждого ключа в `gradients.json` создаётся `gradients/{id}.png` (полоса 10×h для `-tile`).

Высота тайла:
- **gradient12** → h = **192** (title cards)
- остальные → h = **96**

### Спрайты

Рендер через ImageMagick: обводка (`stroke`) + заливка градиентным тайлом. Размер canvas — `w`×`h` из `sprites.json`. Pointsize по умолчанию: **56** (h=96), **112** (h=192); переопределяется `--pointsize`.
