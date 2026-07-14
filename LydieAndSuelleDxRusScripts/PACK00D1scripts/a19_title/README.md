# a19_title — патч UI-текстуры и раскладка uil

Папка содержит патч главного меню title screen:

| Файл | Назначение |
|------|------------|
| `patch.json` | Координаты и PNG на атласе (`w`, `h`, `x`, `y`) |
| `uil_a19_title.xml` | Экранная раскладка (атрибут `pos`) |
| `*.png` | Подменяемые спрайты |

`repack_g1t.py a19_title` собирает `.g1t`, обновляет `uis_gen_a19_title.xml` и копирует `uil_*.xml` в `build/PACK02_patch/saves/ui_en/a19_title/`.

Размеры `w` / `h` для формул ниже — **ширина и высота спрайта на атласе в пикселях** (= поля `w`/`h` в `patch.json`, = `uvwh_w/2` и `uvwh_h/2` в `uis_gen_*.xml`).

## Система координат

- Layout-координаты: **1280×720 (HD)**.
- Центр экрана: **(640, 360)**.
- `pos` в `uil` — **локальные** координаты относительно родительского `<node>`.
- Абсолютная позиция = сумма `pos` по цепочке предков до `<root>`.

Атрибут `scale="scaleX, scaleY, scaleZ"`: если отсутствует, `scaleX = scaleY = 1`.

## Формула по X

```
pos.x = center_x − w × scaleX / 3
```

`center_x` — эффективный центр для данного уровня иерархии. Округление: `round()`.

### Root-элементы

Прямые дети `<root>` (и `press_start` без `pos`, т.е. 0,0,0):

```
pos.x = 640 − w × scaleX / 3
```

| Элемент | w | scaleX | pos.x |
|---------|---|--------|-------|
| logo | 1094 | 0.95 | 294 |
| copyright | 960 | 1.0 | 320 |
| anybutton (EN) | 460 | 1.0 | 487 |
| anybutton (RU) | 700 | 1.0 | 407 |

Проверка logo: `640 − 1094×0.95/3 = 294`.

### Дочерние элементы

```
pos.x = (640 − parent_abs_x) − w × scaleX / 3
```

`parent_abs_x` — сумма `pos.x` всех предков.

#### Пункты меню

Цепочка: `title_menu` (514) → `menu` (−28) → `<image>`.

```
parent_abs_x = 514 + (−28) = 486
base_x = 640 − 486 = 154

pos.x = 154 − w × scaleX / 3
```

Эквивалентная запись: `154 = 640 − 514 − 28`.

Таблица для RU-ширин из `patch.json` (`scaleX = 1`):

| uil name | w | pos.x = round(154 − w/3) |
|----------|---|--------------------------|
| new_game | 350 | 37 |
| load_game | 450 | 4 |
| network_load | 400 | 21 |
| setting | 300 | 54 |
| extra | 250 | 71 |
| end_game | 250 | 71 |

## Формула по Y

Аналогично X, но диапазон **0…720** и используется **высота `h`**:

```
pos.y = center_y − h × scaleY / 3
```

- **Root:** `center_y = 360`, т.е. `pos.y = 360 − h × scaleY / 3`.
- **Дочерние:** `pos.y = (360 − parent_abs_y) − h × scaleY / 3`.

`scaleY` — второй компонент `scale` (по умолчанию 1).

При замене PNG у пунктов меню `h` обычно не меняется (88 px) — `pos.y` оставляют из vanilla. Пересчитывать, если `h` изменился в `patch.json`.

## Workflow

1. Обновить `w`/`h` (и при необходимости `x`/`y` на атласе) в `patch.json`.
2. Пересчитать `pos.x` / `pos.y` в `uil_a19_title.xml`.
3. Запустить repack:

```bash
cd LydieAndSuelleDxRusScripts
python3 PACK00D1scripts/repack_g1t.py a19_title
```

## uvwh (справка)

В `uis_gen_*.xml`: `uvwh_w = 2 × w`, `uvwh_h = 2 × h` (виртуальные координаты текстуры). На расчёт `pos` в uil это не влияет — там используются atlas `w`/`h` напрямую.
