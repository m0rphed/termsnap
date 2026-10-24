"""
Блочные элементы (U+2580-259F): половины, доли в одну восьмую, штриховка, квадранты.
"""

from termsnap.png.boxes.tile import Tile
from termsnap.png.pixels import blend

#: На сколько равных долей делятся клетка у блоков "восьмые" (U+2581-2588, U+2589-258F, U+2594, U+2595).
_EIGHTHS = 8

#: Верхняя и правая половины, верхняя и правая восьмые доли.
_UPPER_HALF, _RIGHT_HALF, _UPPER_EIGHTH, _RIGHT_EIGHTH = 0x2580, 0x2590, 0x2594, 0x2595

#: Нижние доли от 1/8 до целой клетки: U+2581 закрашивает 1/8 снизу, U+2588 - всю клетку.
_LOWER_EIGHTHS = range(0x2581, 0x2589)

#: Левые доли от 7/8 до 1/8: U+2589 закрашивает 7/8 слева, U+258F - 1/8.
_LEFT_EIGHTHS = range(0x2589, 0x2590)

#: Штриховые блоки (светлая, средняя и темная): доля цвета текста, остальное - фон.
_SHADES = {0x2591: 0.25, 0x2592: 0.5, 0x2593: 0.75}

#: Квадранты U+2596-259F: какие четверти клетки закрашены (верх-лево, верх-право, низ-лево, низ-право).
_QUADRANTS = {
    0x2596: (0, 0, 1, 0),
    0x2597: (0, 0, 0, 1),
    0x2598: (1, 0, 0, 0),
    0x2599: (1, 0, 1, 1),
    0x259A: (1, 0, 0, 1),
    0x259B: (1, 1, 1, 0),
    0x259C: (1, 1, 0, 1),
    0x259D: (0, 1, 0, 0),
    0x259E: (0, 1, 1, 0),
    0x259F: (0, 1, 1, 1),
}

#: Положение четвертей в порядке значений ``_QUADRANTS``: (столбец, строка) из двух столбцов и двух строк.
_QUADRANT_CELLS = ((0, 0), (1, 0), (0, 1), (1, 1))


def draw_block(tile: Tile, code: int) -> None:
    """
    Закрашивает клетку по коду блочного элемента; доли считаются от размера клетки, поэтому соседние клетки смыкаются.
    """
    x0, y0, x1, y1 = tile.left, tile.top, tile.right, tile.bottom
    w, h = tile.width, tile.height
    if code == _UPPER_HALF:
        tile.fill(x0, y0, x1, y0 + h / 2)
    elif code in _LOWER_EIGHTHS:
        tile.fill(x0, y1 - h * (code - _LOWER_EIGHTHS.start + 1) / _EIGHTHS, x1, y1)
    elif code in _LEFT_EIGHTHS:
        tile.fill(x0, y0, x0 + w * (_LEFT_EIGHTHS.stop - code) / _EIGHTHS, y1)
    elif code == _RIGHT_HALF:
        tile.fill(x0 + w / 2, y0, x1, y1)
    elif code in _SHADES:
        tile.fill(x0, y0, x1, y1, blend(tile.foreground, tile.background, _SHADES[code]))
    elif code == _UPPER_EIGHTH:
        tile.fill(x0, y0, x1, y0 + h / _EIGHTHS)
    elif code == _RIGHT_EIGHTH:
        tile.fill(x1 - w / _EIGHTHS, y0, x1, y1)
    elif code in _QUADRANTS:
        for (column, row), filled in zip(_QUADRANT_CELLS, _QUADRANTS[code], strict=True):
            if filled:
                tile.fill(x0 + w * column / 2, y0 + h * row / 2, x0 + w * (column + 1) / 2, y0 + h * (row + 1) / 2)
