# Length patches — EBM, dialog, recipe и quest UI copy limits

In-place патчи steamless-unpacked exe: увеличение лимитов буферов строк в коде загрузчика EBM, hot-функции диалога, кластера условий рецепта / награды-предмета и целей квеста.
Часть release-пайплайна `LydieAndSuelleDxRusScripts/`.

## Лимиты

| Патч | Vanilla | Patched | Сайтов |
|------|---------|---------|--------|
| EBM event message | 400 B | 800 B | 49 |
| Dialog string | 256 B | 512 B | 9 |
| Recipe UI copy (+ quest item reward) | 32 / 64 B | 128 B | 13 |
| Quest etc copy | 64 B @ [rbp-0x40] | 128 B @ [rbp-0x80] | 14 |

Все замены **одинакового размера** — размер exe не меняется.

## Регионы VA

| Патч | Регион |
|------|--------|
| EBM | `0x1401DD000`–`0x1401DF000` (+ string layer `0x1DD580`–`0x1DDE20`) |
| Dialog | `0x140303020`–`0x1403031A0` |
| Recipe UI copy A | `0x1404136A5`, `0x14041372E`, `0x1404137DC`, `0x140413882` |
| Recipe UI copy B | `0x1403E5D45`, `0x1403E5DDD`, `0x1403E5E85`, `0x1403E5F25` |
| Reward `%s[%d/%d]` A | `0x14041432B`, `0x14041449B`, `0x140414BA2` (crash) |
| Reward `%s[%d/%d]` B | `0x1403E5B4B`, `0x1403E600A` |
| Quest etc copy | `0x14003A0AA` (sub rsp), `0x14003A174` (struct[0]), `0x14003A1D0`/`0x14003A312` (lea copy/read), `0x14003A238`/`0x14003A2A1` (alt-path), `0x14003A215`/`0x14003A3CA`/`0x14003A3D2`/`0x14003A3DA` (rsp restore), `0x14003A3ED`/`0x14003A402`/`0x14003A410` (add rsp) |

Не пересекаются с phys_glyph (glyph table data ~`0xC1FFxx` / `~0xC236xx`).

### Краш 6619426 (recipe)

Два зеркальных кластера, один CRT-путь `+0xa9a0` → `+0x85ad18`:

| Кластер | WinDbg | Caller |
|---------|--------|--------|
| A | windbg_v2 | `+0x4136AA` |
| B | windbg_v3 | `+0x3E5D4A` |

Патч `+0x37e040` (ui_string_length) **не участвует** — см. архив ниже.

### Краш item reward (`%s[%d/%d]`)

WinDbg `work/errors/reward_item_error/windbg_v1.txt`: caller `+0x414bb0` ← `+0xa9a0`; `mov edx,64` @ `0x140414BA2` formats **`%s[%d/%d]`** (длинное RU-имя предмета). Те же три UI (`quest_receive` / `quest_report` / `summary01`, рядом с `STR_UI_0073` / `6619210`). Пять сайтов 64→128 в кластерах A/B рядом с recipe.

### Краш 4980738 (quest objective)

WinDbg `work/errors/unknow_error/windbg_v1.txt`: caller `+0x3A1E1`, stack arg `0x004C0002` = String_No **4980738** (`Obtain %s.` / `Получить %s.`). Тот же путь покрывает **4980737** (`Defeat %s.` / `Победить %s.`).

Патч v6.1 (partial shift + rsp restore): frame `sub/add rsp 0x80→0xC0`; main buffer write/read @ `[rbp-0x80]` + `mov edx,128`; struct meta @ `[rbp-0x38..-0x08]` без изменений; alt-path через `lea rcx,[rbp-0x80]` + `movaps [rcx-0x20]` (alt @ `[rbp-0xA0]`); rsp restore imm32 `+0x40` для r12/r14/rsi/rbx (windbg_v3: AV @ `+0x3A6A0`, rbx=0). 14 same-size sites.

Откат на v2 (2 sites: только `lea rcx` + `mov edx`, read @ `[rbp-0x40]`) — если save-load или HUD ломается.

## JSON-артефакты (`build/exe/length_patches/`)

| Файл | Описание |
|------|----------|
| `ebm_length_patches.json` | manifest EBM |
| `dialog_length_patches.json` | manifest dialog |
| `recipe_ui_copy_limit_patches.json` | manifest recipe UI copy + reward (13 sites) |
| `quest_etc_copy_limit_patches.json` | manifest quest etc copy (14 sites, v6.1) |

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `ebm_length_patch.py` | library: `apply_ebm_length_patch(exe)` |
| `dialog_length_patch.py` | library: `apply_dialog_length_patch(exe)` |
| `recipe_ui_copy_limit_patch.py` | library: `apply_recipe_ui_copy_limit_patch(exe)` |
| `quest_etc_copy_limit_patch.py` | library: `apply_quest_etc_copy_limit_patch(exe)` |
| `patch_ebm_length.py` | CLI: standalone EBM |
| `patch_dialog_length.py` | CLI: standalone dialog |
| `patch_recipe_ui_copy_limit.py` | CLI: standalone recipe UI copy |
| `patch_quest_etc_copy_limit.py` | CLI: standalone quest etc copy |

## Архив (не в release chain)

| Путь | Описание |
|------|----------|
| `archives/exe_patches/length_patches/ui_string_length_patch.py` | Патч `+0x37e040` (256→512); не фиксит 6619426 |
| `archives/exe_patches/length_patches/patch_ui_string_length.py` | Ручной CLI |

## Команды

```bash
cd LydieAndSuelleDxRusScripts

# Через оркестратор (рекомендуется)
python3 exe_patches/patch_exe.py
python3 exe_patches/patch_exe.py --no-phys-glyph   # только length

# Standalone recipe fix
python3 exe_patches/length_patches/patch_recipe_ui_copy_limit.py \
  --exe-in steamless/Atelier_Lydie_and_Suelle_DX.exe.unpacked.exe \
  --exe-out /tmp/recipe_test.exe

# Standalone quest fix
python3 exe_patches/length_patches/patch_quest_etc_copy_limit.py \
  --exe-in steamless/Atelier_Lydie_and_Suelle_DX.exe.unpacked.exe \
  --exe-out /tmp/quest_test.exe
```

## Пути и деплой

| Роль | Путь |
|------|------|
| Вход exe | `steamless/Atelier_Lydie_and_Suelle_DX.exe.unpacked.exe` |
| Выход exe (full chain) | `build/out/Atelier_Lydie_and_Suelle_DX.exe` |
| JSON | `build/exe/length_patches/` |

После сборки **скопировать** `build/out/Atelier_Lydie_and_Suelle_DX.exe` в папку Steam.
Повторное применение на полностью пропатченный exe — no-op (idempotent). Сборка всегда из чистого steamless.

## WinDbg (после деплоя)

```
u Atelier_Lydie_and_Suelle_DX+0x3a0aa L2   # sub rsp,0C0h
u Atelier_Lydie_and_Suelle_DX+0x3a1d0 L2   # lea rcx,[rbp-80h]
u Atelier_Lydie_and_Suelle_DX+0x3a312 L2   # lea rdx,[rbp-80h]
u Atelier_Lydie_and_Suelle_DX+0x3a3d6 L1   # mov rbx,[rsp+0E0h]
u Atelier_Lydie_and_Suelle_DX+0x3a211 L1   # mov r12,[rsp+0F0h]
u Atelier_Lydie_and_Suelle_DX+0x3a410 L2   # add rsp,0C0h
bp Atelier_Lydie_and_Suelle_DX+0x3a1dc
g
# edx=128, copy dest = rbp-0x80
```
