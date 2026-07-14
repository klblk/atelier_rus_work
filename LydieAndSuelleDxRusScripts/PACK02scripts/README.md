# PACK02 — text_en + ui_en patching

## text_en encoding

Применяет строки из `strings/debug/strings.json` к `str_*.xml` и `strcombineall.xml`.

| Роль | Путь |
|------|------|
| Каталог | `strings/debug/strings.json` (`source: pack02_text_en`) |
| Vanilla XML | `extracts/pack_extracts/PACK02_extract/saves/text_en/` |
| Выход | `build/PACK02_patch/saves/text_en/` |

На каждое изменение патчатся **layer file** и **`strcombineall.xml`**. Неизменённые файлы в patch не копируются.

### Режимы (`encode_text_en.py --mode`)

См. [`PACKutils_scripts/README.md`](../PACKutils_scripts/README.md) — `translated` / `full` / `none`.

## UI string_id patching

Добавляет `string_id="STR_UI_...."` к hardcoded `<text text="..."/>` в `uil_*.xml` по [`ui_strings.json`](ui_strings.json).

| Роль | Путь |
|------|------|
| Конфиг | `PACK02scripts/ui_strings.json` |
| Vanilla UI | `extracts/.../PACK02_extract/saves/ui_en/` |
| Выход | `build/PACK02_patch/saves/ui_en/` (только изменённые `uil_*.xml`) |
| ID map (генерация) | `PACK02scripts/ui_string_id_map.json` |

```bash
python3 PACK02scripts/build_ui_string_id_map.py   # обновить map из str_ui*.xml
python3 PACK02scripts/patch_ui_strings.py --dry-run
python3 PACK02scripts/patch_ui_strings.py
```

## Полный pipeline PACK02

```bash
cd LydieAndSuelleDxRusScripts

python3 exe_patches/patch_exe.py
python3 PACK02scripts/build_ui_string_id_map.py   # при необходимости
python3 PACK02scripts/patch_ui_strings.py
python3 PACK02scripts/encode_text_en.py
python3 PACKutils_scripts/repack_pack.py PACK02
# → build/out/Data/PACK02.PAK
```

## Модули

| Файл | Назначение |
|------|------------|
| `pack02_xml.py` | `Pack02XmlCache`, патч text_en по `String_No` |
| `encode_text_en.py` | encode/apply переводов text_en |
| `build_ui_string_id_map.py` | `str_ui.xml` → `ui_string_id_map.json` |
| `patch_ui_strings.py` | `string_id` в ui_en layout XML |
| `ui_strings.json` | text → String_No / string_id map |
