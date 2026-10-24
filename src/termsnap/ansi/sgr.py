"""
Применение последовательности SGR (``ESC [ ... m``) к стилю.
"""

from dataclasses import replace

from termsnap.ansi import codes
from termsnap.ansi.tokens import number
from termsnap.model import PLAIN, Color, Indexed, Rgb, Style


def _color(values: list[int]) -> Color | None:
    """
    Цвет из значений после кода 38 или 48: ``5, n`` (палитра) или ``2, r, g, b`` (24 бита); в записи через
    двоеточия перед ``r`` может стоять идентификатор цветового пространства, поэтому берутся последние три числа.
    """
    try:
        match values:
            case [codes.COLOR_PALETTE, index, *_]:
                return Indexed(index)
            case [codes.COLOR_TRUECOLOR, _, _, _, *_]:
                return Rgb(*values[-3:])
    except ValueError:  # число вне 0-255: цвет не задан
        pass
    return None


def _read_extended_color(group: list[int], following: list[list[int]]) -> tuple[Color | None, int]:
    """
    Цвет после кода 38 или 48 и сколько следующих групп он занял. Две записи одного и того же:

        38:5:208          одна группа [38, 5, 208]: значения внутри группы, following не нужны
        38;5;208          три группы [38] [5] [208]: значения лежат в следующих группах
    """
    if len(group) > 1:
        return _color(group[1:]), 0
    values = [next_group[0] for next_group in following]
    length = codes.EXTENDED_LENGTH.get(values[0], len(values)) if values else 0  # неизвестный вид съедает все остальное
    return _color(values[:length]), length


def apply_sgr(style: Style, params: str) -> Style:
    """
    Новый стиль после последовательности SGR с параметрами ``params`` (текст между ``[`` и ``m``).
    """
    # "1;31" -> [[1], [31]];  "38:2::1:2:3" -> [[38, 2, 0, 1, 2, 3]];  "" -> [[0]] (пустой список параметров - сброс)
    groups = [[number(part) for part in group.split(":")] for group in params.split(";")] if params else [[0]]
    position = 0
    while position < len(groups):
        group = groups[position]
        position += 1
        match group[0]:
            case codes.RESET:
                style = PLAIN
            case codes.BOLD:
                style = replace(style, bold=True)
            case codes.DIM:
                style = replace(style, dim=True)
            case codes.ITALIC:
                style = replace(style, italic=True)
            case codes.UNDERLINE | codes.DOUBLE_UNDERLINE:
                style = replace(style, underline=True)
            case codes.INVERSE:
                style = replace(style, inverse=True)
            case codes.STRIKE:
                style = replace(style, strike=True)
            case codes.NORMAL_INTENSITY:
                style = replace(style, bold=False, dim=False)
            case codes.NO_ITALIC:
                style = replace(style, italic=False)
            case codes.NO_UNDERLINE:
                style = replace(style, underline=False)
            case codes.NO_INVERSE:
                style = replace(style, inverse=False)
            case codes.NO_STRIKE:
                style = replace(style, strike=False)
            case code if code in codes.FG_BASIC:
                style = replace(style, fg=Indexed(code - codes.FG_BASIC.start))
            case code if code in codes.FG_BRIGHT:
                style = replace(style, fg=Indexed(code - codes.FG_BRIGHT.start + codes.BRIGHT_OFFSET))
            case code if code in codes.BG_BASIC:
                style = replace(style, bg=Indexed(code - codes.BG_BASIC.start))
            case code if code in codes.BG_BRIGHT:
                style = replace(style, bg=Indexed(code - codes.BG_BRIGHT.start + codes.BRIGHT_OFFSET))
            case codes.FG_DEFAULT:
                style = replace(style, fg=None)
            case codes.BG_DEFAULT:
                style = replace(style, bg=None)
            case codes.FG_EXTENDED | codes.BG_EXTENDED as code:
                color, taken = _read_extended_color(group, groups[position:])
                position += taken
                style = replace(style, fg=color) if code == codes.FG_EXTENDED else replace(style, bg=color)
            case _:
                pass  # мигание, скрытый текст, шрифты и прочее: на показ в документе не влияет
    return style
