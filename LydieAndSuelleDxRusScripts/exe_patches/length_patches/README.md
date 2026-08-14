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

v6.2 (PATH_B je rel8): `lea rdx,[rbp-0xA0]` на 7 B сдвинул null-ветки; `je +0x28/+0x1A` правим на `+0x2B/+0x1D` (join `+0x3A30D`).

v6.3 (HUD «999 ост. дн.»): переписанные PATH_A/B сохранили vanilla rel32 при сдвиге VA. PATH_B `lea r8`/`lea rdx` попадали в `"ays"`/`"3d"` вместо `"%3d"`/`"days"` → `GetString` null → `SetText` дней пропускается, на поле остаётся XML-заглушка `999`. Заодно E8: PATH_B copy/GetString на −3, PATH_A все три call на −13; PATH_A dest/SetText — `lea [rbp-0xA0]`.

Откат на v2 (2 sites: только `lea rcx` + `mov edx`, read @ `[rbp-0x40]`) — если save-load или HUD ломается.

### Краш get_item (PATH_B join)

WinDbg `work/errors/get_item_error/windbg_v1.txt`: AV read `0x78` @ `+0x3a30f` (`push [rax+48h]`, `rax=0x30`), стек пустой. Подбор предмета идёт в PATH_B (`0x14003A2A1`); после v6 `lea rdx,[rbp-0xA0]` (4 B → 7 B) `je +0x28` / `je +0x1A` попадали в `+0x3A30A` (середина инструкции) вместо join `+0x3A30D`. v6.2: `je +0x2B` @ `0x14003A2E0`, `je +0x1D` @ `0x14003A2EE`; `EB 0C` без изменений. PATH_A не затронут.

### HUD 999 дней (PATH_B RIP/E8)

После v6.2 подбор не крашится, но полевой HUD показывает **«999 ост. дн.»** (XML-заглушка `days` + `STR_UI_0054`). Vanilla PATH_B: `sprintf("%3d", r14d)` @ `0x140986C74`, `GetString(..., "days")` @ `0x140986C78`, `SetText`. v6 сдвинул insn VA, сырой disp32 остался — format/name стали `"ays"`/`"3d"`. v6.3 пересчитывает RIP/E8 в PATH_A и PATH_B; PATH_A dest/SetText — `[rbp-0xA0]`.

## JSON-артефакты (`build/exe/length_patches/`)

| Файл | Описание |
|------|----------|
| `ebm_length_patches.json` | manifest EBM |
| `dialog_length_patches.json` | manifest dialog |
| `recipe_ui_copy_limit_patches.json` | manifest recipe UI copy + reward (13 sites) |
| `quest_etc_copy_limit_patches.json` | manifest quest etc copy (14 sites, v6.3) |

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
u Atelier_Lydie_and_Suelle_DX+0x3a2e0 L1   # je +0x2B -> +0x3A30D
u Atelier_Lydie_and_Suelle_DX+0x3a2ee L1   # je +0x1D -> +0x3A30D
u Atelier_Lydie_and_Suelle_DX+0x3a312 L2   # lea rdx,[rbp-80h]
u Atelier_Lydie_and_Suelle_DX+0x3a3d6 L1   # mov rbx,[rsp+0E0h]
u Atelier_Lydie_and_Suelle_DX+0x3a211 L1   # mov r12,[rsp+0F0h]
u Atelier_Lydie_and_Suelle_DX+0x3a410 L2   # add rsp,0C0h
u Atelier_Lydie_and_Suelle_DX+0x3a2b3 L1   # lea r8, "%3d" @ 0x140986C74
u Atelier_Lydie_and_Suelle_DX+0x3a2cd L1   # lea rdx, "days" @ 0x140986C78
u Atelier_Lydie_and_Suelle_DX+0x3a2c3 L1   # call copy 0x14000A9A0
u Atelier_Lydie_and_Suelle_DX+0x3a2d8 L1   # call GetString 0x140339190
u Atelier_Lydie_and_Suelle_DX+0x3a254 L1   # PATH_A lea rcx,[rbp-0A0h]
u Atelier_Lydie_and_Suelle_DX+0x3a26d L1   # PATH_A lea rdx,[rbp-0A0h]
```
