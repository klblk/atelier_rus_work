# Atelier Lydie & Suelle DX — инструменты русификации

Набор Python-скриптов для сборки русификатора **Atelier Lydie & Suelle DX** (DX-версия). Патчит exe (кириллица в шрифте), кодирует строки в PAK, собирает UI-текстуры.

Скрипты разрабатывались **с помощью нейросети Cursor AI** — часть кода и документации могла быть сгенерирована или отредактирована с её участием.

Разработка и тестирование велись на **Linux**; на других ОС (Windows, macOS) работа **не гарантируется**.

Игровые файлы в репозиторий **не входят** — для работы нужна легальная копия игры.

## Быстрый старт

Три шага в [`LydieAndSuelleDxRusScripts/`](LydieAndSuelleDxRusScripts/):

```bash
cd LydieAndSuelleDxRusScripts

python3 init_tools.py          # gust_tools + compress_bc3 (обязательный шаг перед init.py)

# Первичная настройка: распаковка PAK, каталог строк.
# Требует оригинальные файлы игры и Steamless-версию exe.
python3 init.py --game-dir /path/to/AtelierLydieAndSuelleDX \
                --steamless-exe /path/to/AtelierLydieAndSuelleDX_Steamless.exe

python3 build_translation.py   # полная сборка патча
```

- [`init_tools.py`](LydieAndSuelleDxRusScripts/init_tools.py) — сборка локальных утилит (`gust_pak`, `gust_ebm`, `compress_bc3`); без них [`init.py`](LydieAndSuelleDxRusScripts/init.py) не сможет распаковать PAK.
- [`init.py`](LydieAndSuelleDxRusScripts/init.py) — одноразовая инициализация: extract PAK/EBM, `collect_strings`; проверяет `Data/*.PAK`, копирует Steamless exe (также вызывает `init_tools.py`, если tools ещё не собраны).
- `--game-dir` и `--steamless-exe` — примеры путей; без легальной копии игры и распакованного exe pipeline не стартует.
- Подробности по подсистемам — в README внутри `LydieAndSuelleDxRusScripts/*/`.

## Отказ от ответственности

- Проект создан фанатами, **не связан** с KOEI TECMO GAMES CO., LTD. и не одобрен ею.
- **Atelier Lydie & Suelle**, серия **Atelier** и все связанные названия, персонажи, сюжет и материалы — интеллектуальная собственность **Koei Tecmo**.
- Репозиторий содержит только инструменты и переводческие данные; распространение игровых ассетов не предполагается.
- Использование — на свой риск; для работы требуется приобретённая копия игры.

---

# Atelier Lydie & Suelle DX — Russian Localization Tooling

A set of Python scripts for building a Russian localization patch for **Atelier Lydie & Suelle DX** (DX edition). Patches the exe (Cyrillic font support), encodes strings into PAK archives, and rebuilds UI textures.

The scripts were developed **with the help of Cursor AI** — parts of the code and documentation may have been generated or edited with its assistance.

Development and testing were done on **Linux**; operation on other operating systems (Windows, macOS) is **not guaranteed**.

Game files are **not included** in this repository — a legally purchased copy of the game is required.

## Quick start

Three steps in [`LydieAndSuelleDxRusScripts/`](LydieAndSuelleDxRusScripts/):

```bash
cd LydieAndSuelleDxRusScripts

python3 init_tools.py          # gust_tools + compress_bc3 (required before init.py)

# One-time setup: unpack PAK files, build the string catalog.
# Requires original game files and a Steamless-unpacked exe.
python3 init.py --game-dir /path/to/AtelierLydieAndSuelleDX \
                --steamless-exe /path/to/AtelierLydieAndSuelleDX_Steamless.exe

python3 build_translation.py   # full patch build
```

- [`init_tools.py`](LydieAndSuelleDxRusScripts/init_tools.py) — builds local utilities (`gust_pak`, `gust_ebm`, `compress_bc3`); [`init.py`](LydieAndSuelleDxRusScripts/init.py) cannot unpack PAK files without them.
- [`init.py`](LydieAndSuelleDxRusScripts/init.py) — one-time initialization: extract PAK/EBM, `collect_strings`; validates `Data/*.PAK`, copies the Steamless exe (also invokes `init_tools.py` if tools are not built yet).
- `--game-dir` and `--steamless-exe` are example paths; the pipeline will not start without a legal game copy and an unpacked exe.
- See README files under `LydieAndSuelleDxRusScripts/*/` for subsystem details.

## Disclaimer

- This is a fan-made project, **not affiliated** with or endorsed by KOEI TECMO GAMES CO., LTD.
- **Atelier Lydie & Suelle**, the **Atelier** series, and all related names, characters, story, and materials are the intellectual property of **Koei Tecmo**.
- This repository contains only tooling and translation data; distribution of game assets is not intended.
- Use at your own risk; a purchased copy of the game is required.

## License

MIT — see [LICENSE](LICENSE).
