"""
Из ячеек экрана pyte в модель termsnap: цвета, стиль, строки.
"""

from itertools import groupby

from pyte.screens import Char

from termsnap.model import PLAIN, Color, Indexed, Line, Rgb, Span, Style
from termsnap.screen.emulator import PALETTE_MARK

#: Названия цветов pyte для кодов 30-37 по порядку (желтый у pyte называется ``brown``); яркие получают приставку
#: ``bright``: ``brightred``.
_PYTE_NAMES = ("black", "red", "green", "brown", "blue", "magenta", "cyan", "white")
_BASIC_COLORS = {name: index for index, name in enumerate(_PYTE_NAMES)} | {
    f"bright{name}": index + 8 for index, name in enumerate(_PYTE_NAMES)
}

#: Ячейка без оформления (текст не важен): с ней сравнивается каждая ячейка, чтобы быстро найти обычный стиль.
_UNSTYLED = Char("")

#: Пустая ячейка: пробел без оформления. Хвост из таких ячеек в строке отбрасывается.
_BLANK = Char(" ")


def color_of(value: str) -> Color | None:
    """
    Цвет из поля ячейки pyte: ``"default"`` -> нет цвета; ``"#208"`` -> индекс палитры; имя (``"red"``) -> индекс
    базового цвета; иначе шесть цифр RGB (``"ff8800"``).
    """
    if value == "default":
        return None
    if value.startswith(PALETTE_MARK):
        return Indexed(int(value[len(PALETTE_MARK) :]))
    if value in _BASIC_COLORS:
        return Indexed(_BASIC_COLORS[value])
    return Rgb.from_hex(value)


def style_of(cell: Char) -> Style:
    """
    Стиль ячейки. Тусклый атрибут лежит в поле ``blink`` (см. ``TerminalScreen``).
    """
    if cell._replace(data="") == _UNSTYLED:
        return PLAIN
    return Style(
        fg=color_of(cell.fg),
        bg=color_of(cell.bg),
        bold=cell.bold,
        dim=cell.blink,
        italic=cell.italics,
        underline=cell.underscore,
        strike=cell.strikethrough,
        inverse=cell.reverse,
    )


def line_of(cells: list[Char]) -> Line:
    """
    Строка из ячеек экрана без хвоста из пустых ячеек; вторая половина широкого символа в тексте пуста, как в
    ``termsnap.ansi``. Соседние ячейки с одним стилем собираются во фрагмент.
    """
    while cells and cells[-1] == _BLANK:
        cells.pop()
    return Line(tuple(Span("".join(cell.data for cell in group), style) for style, group in groupby(cells, style_of)))
