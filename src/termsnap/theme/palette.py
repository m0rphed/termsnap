"""
Палитра терминала: названия 16 базовых цветов и расчет цветов 16-255 по правилам xterm.
"""

from termsnap.model import Rgb

#: Названия 16 базовых цветов по порядку номеров (0-7 обычные, 8-15 яркие).
ANSI_NAMES = (
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
)  # fmt: skip

#: Номера, с которых начинаются части расширенной палитры xterm: после 16 базовых идет куб цветов, затем серые ступени.
CUBE_START = 16
GRAY_START = 232

#: Уровни одного канала в кубе 6x6x6 (индексы 16-231), как в xterm: 0, затем 55 + 40 * n для n от 1 до 5.
CUBE_LEVELS = (0, 95, 135, 175, 215, 255)

#: Сторона куба: по шесть уровней на канал.
CUBE_SIDE = len(CUBE_LEVELS)

#: Серые ступени (индексы 232-255): 24 значения от 8 с шагом 10, без чистого черного и белого (они есть в кубе).
GRAY_FIRST_LEVEL = 8
GRAY_STEP = 10


def ansi_index(key: int | str) -> int:
    """
    Номер базового цвета по номеру или названию (``"red"``, ``"bright-red"``, ``"Bright Red"``).
    """
    if isinstance(key, int):
        if not 0 <= key < len(ANSI_NAMES):
            raise ValueError(f"номер базового цвета от 0 до {len(ANSI_NAMES) - 1}, получено {key}")
        return key
    name = key.strip().casefold().replace("-", "_").replace(" ", "_")
    if name not in ANSI_NAMES:
        raise ValueError(f"неизвестный базовый цвет {key!r}; допустимы номера 0-15 и названия {', '.join(ANSI_NAMES)}")
    return ANSI_NAMES.index(name)


def extended_color(index: int) -> Rgb:
    """
    Цвет из расширенной палитры xterm (индексы 16-255); он не зависит от темы.

        16..231:  n = index - 16;  красный, зеленый, синий = цифры n в шестеричной записи (n = 36*r + 6*g + b);
                  каждая цифра -> CUBE_LEVELS[цифра]
        232..255: серый уровень 8 + 10 * (index - 232)
    """
    if index < GRAY_START:
        cube = index - CUBE_START
        red, green, blue = cube // CUBE_SIDE**2, cube // CUBE_SIDE % CUBE_SIDE, cube % CUBE_SIDE
        return Rgb(CUBE_LEVELS[red], CUBE_LEVELS[green], CUBE_LEVELS[blue])
    level = GRAY_FIRST_LEVEL + GRAY_STEP * (index - GRAY_START)
    return Rgb(level, level, level)
