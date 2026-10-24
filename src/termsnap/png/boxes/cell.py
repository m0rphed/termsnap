"""
Точка входа псевдографики: нарисовать символ в клетке, если его рисует сама библиотека.
"""

from PIL import ImageDraw

from termsnap.png.boxes.arms import arms_of
from termsnap.png.boxes.blocks import draw_block
from termsnap.png.boxes.braille import draw_braille
from termsnap.png.boxes.lines import draw_lines
from termsnap.png.boxes.ranges import BLOCK_ELEMENTS, BOX_DRAWINGS, BRAILLE
from termsnap.png.boxes.tile import Tile
from termsnap.png.pixels import Channels


def draw_cell(
    draw: ImageDraw.ImageDraw,
    char: str,
    box: tuple[float, float, float, float],
    foreground: Channels,
    background: Channels,
    light: int,
) -> bool:
    """
    Рисует символ псевдографики в клетке ``box`` = (левый, верхний, правый, нижний край) и возвращает ``True``;
    для остальных символов ничего не рисует и возвращает ``False`` (их рисует шрифт). ``light`` - толщина
    тонкой линии в пикселях.
    """
    if len(char) != 1:
        return False
    code = ord(char)
    tile = Tile(draw, *box, foreground, background, light)
    if code in BOX_DRAWINGS:
        arms = arms_of(char)
        if arms is None:  # диагонали: их рисует шрифт
            return False
        draw_lines(tile, arms)
    elif code in BLOCK_ELEMENTS:
        draw_block(tile, code)
    elif code in BRAILLE:
        draw_braille(tile, code)
    else:
        return False
    return True


def is_box_char(char: str) -> bool:
    """
    Рисуется ли символ самой библиотекой (``draw_cell`` вернет ``True``).
    """
    code = ord(char) if len(char) == 1 else 0
    if code in BOX_DRAWINGS:
        return arms_of(char) is not None
    return code in BLOCK_ELEMENTS or code in BRAILLE
