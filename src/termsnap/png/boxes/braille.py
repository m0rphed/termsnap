"""
Шрифт Брайля (U+2800-28FF): точки в сетке 2 x 4.
"""

from termsnap.png.boxes.ranges import BRAILLE
from termsnap.png.boxes.tile import Tile

#: Бит кода -> (столбец, строка) точки в сетке 2 столбца x 4 строки. Код символа - 0x2800 плюс восемь битов, по биту
#: на точку: биты 0-2 - левый столбец сверху вниз, 3-5 - правый, затем нижние точки (бит 6 слева, бит 7 справа).
_DOT_POSITIONS = {0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (0, 3), 7: (1, 3)}

#: Где стоят центры точек, в долях размера клетки: по горизонтали начало и шаг между столбцами, по вертикали то же
#: между строками (четыре строки делят клетку на четверти, точка в центре четверти).
_DOT_X_START, _DOT_X_STEP = 0.28, 0.44
_DOT_Y_START, _DOT_Y_STEP = 0.125, 0.25

#: Радиус точки в долях ширины и высоты клетки; берется меньший, чтобы точка осталась круглой в любой клетке.
_DOT_RADIUS_OF_WIDTH, _DOT_RADIUS_OF_HEIGHT = 0.14, 0.08


def draw_braille(tile: Tile, code: int) -> None:
    """
    Рисует круглые точки, соответствующие установленным битам кода.
    """
    radius = min(tile.width * _DOT_RADIUS_OF_WIDTH, tile.height * _DOT_RADIUS_OF_HEIGHT)
    for bit, (column, row) in _DOT_POSITIONS.items():
        if ((code - BRAILLE.start) >> bit) & 1:
            x = tile.left + tile.width * (_DOT_X_START + _DOT_X_STEP * column)
            y = tile.top + tile.height * (_DOT_Y_START + _DOT_Y_STEP * row)
            tile.draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=tile.foreground)
