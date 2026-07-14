# PACK01 — event EBM

## Extract EBM JSON

Batch-extract `event_message_*.ebm` → JSON sidecar для каталога строк.

```bash
cd LydieAndSuelleDxRusScripts

# Prerequisite: PACK01 extract
python3 PACKutils_scripts/extract_packs.py

python3 PACK01scripts/extract_pack01_event_ebm.py
python3 PACK01scripts/extract_pack01_event_ebm.py --force -j 4
```

Выход: `extracts/PACK01_event_ebm_extract/event/event_en/` (symlink на `.ebm` + `.json`).

## Encode event EBM

Применяет строки из `strings/debug/strings.json` к event EBM через JSON sidecar и `gust_ebm`.

## Вход / выход

| Роль | Путь |
|------|------|
| Каталог | `strings/debug/strings.json` (`source: pack01_ebm`) |
| EBM JSON | `extracts/PACK01_event_ebm_extract/event/event_en/` |
| Выход | `build/PACK01_patch/event/event_en/{chapter}/event_message_*.ebm` |

В patch попадают **только изменённые** `.ebm` (без JSON).

## Режимы (`--mode`)

| Режим | Поведение |
|-------|-----------|
| `translated` (default) | Только строки с непустым `translation` → encode |
| `full` | Все записи каталога: `encode(translation)` или `encode(original)` |
| `none` | Только с переводом: подставить `translation` без encode |

## Команды

```bash
cd LydieAndSuelleDxRusScripts

# Prerequisite: carrier map
python3 exe_patches/patch_exe.py

# Только переведённые (default)
python3 PACK01scripts/encode_event_ebm.py

# Полный encode всех catalog original
python3 PACK01scripts/encode_event_ebm.py --mode full

# Без encode, plain translation
python3 PACK01scripts/encode_event_ebm.py --mode none

# Dry-run
python3 PACK01scripts/encode_event_ebm.py --mode full --dry-run
```

## CLI

- `--ebm-limit-bytes` — max UTF-8 длина `msg_string` после encode (default: `800`)
- `--strings-json`, `--ebm-json-root`, `--out-root`, `--resolved`, `--dry-run`

## Модули

- `extract_pack01_event_ebm.py` — EBM → JSON sidecar
- `gust_ebm_tools.py` — `load_gust_json`, `dump_gust_json`, `rebuild_ebm_from_json`
- `encode_event_ebm.py` — apply/encode переводов в EBM
