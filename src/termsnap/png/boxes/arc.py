"""
Скругленные углы рамок (U+256D-2570): дуга окружности со сглаживанием.
"""

import math
from functools import cache

from termsnap.png.boxes.arms import Arms
from termsnap.png.boxes.tile import Tile
from termsnap.png.pixels import blend, pixel

#: Сглаживание: каждый пиксель делится на SUBSAMPLES x SUBSAMPLES подточек, доля попавших под линию - это доля цвета.
SUBSAMPLES = 5


def draw_arc(tile: Tile, arms: Arms) -> None:
    """
    Скругленный угол: дуга окружности, которая соединяет середины двух соседних сторон клетки. Линия сглажена; ее ось
    совпадает с осью прямых линий в соседних клетках (те же пиксельные границы), поэтому стык незаметен.
    """
    thickness = tile.light
    px0, py0, px1, py1 = pixel(tile.left), pixel(tile.top), pixel(tile.right), pixel(tile.bottom)
    # столбцы вертикальной линии и строки горизонтальной - ровно те, что закрасил бы ``Tile.fill``
    left = pixel(tile.center_x - thickness / 2)
    right = pixel(tile.center_x + thickness / 2)
    top = pixel(tile.center_y - thickness / 2)
    bottom = pixel(tile.center_y + thickness / 2)
    coverage = arc_coverage(
        px1 - px0, py1 - py0, (left - px0, right - px0), (top - py0, bottom - py0), bool(arms.right), bool(arms.down)
    )
    for (i, j), share in coverage.items():
        tile.draw.point((px0 + i, py0 + j), fill=blend(tile.foreground, tile.background, share))


@cache
def arc_coverage(
    width: int, height: int, columns: tuple[int, int], rows: tuple[int, int], right: bool, down: bool
) -> dict[tuple[int, int], float]:
    """
    Доли закраски пикселей клетки ``width`` x ``height`` под скругленным углом (``right``, ``down`` - куда идут
    линии из центра). ``columns`` и ``rows`` - границы вертикальной и горизонтальной линий. Угол - дуга окружности
    радиуса в полклетки по ширине и прямые концы до границ клетки. Результат запоминается: углов в рамке много,
    а расчет по подточкам дорогой.

        центр окружности лежит по ту же сторону от центра клетки, куда идут линии, на расстоянии радиуса
        для каждой подточки пикселя:
            на участке дуги             -> закрашена, если расстояние до центра окружности ~ радиусу
                                           (допуск - полутолщина линии)
            на прямом конце вертикали   -> закрашена, если ближе полутолщины к оси вертикали
            на прямом конце горизонтали -> то же для оси горизонтали
        доля пикселя = закрашенные подточки / все подточки
    """
    half = max(columns[1] - columns[0], rows[1] - rows[0]) / 2  # полутолщина линии
    axis_x, axis_y = sum(columns) / 2, sum(rows) / 2  # оси вертикальной и горизонтальной линий
    step_x, step_y = (1 if right else -1), (1 if down else -1)
    # радиус на пиксель короче расстояния до границы клетки: у дуги остается прямой конец, и в соседнюю клетку
    # линия входит ровно
    radius = max(min(abs((width if right else 0) - axis_x), abs((height if down else 0) - axis_y)) - 1, 1)
    center_x, center_y = axis_x + step_x * radius, axis_y + step_y * radius
    result: dict[tuple[int, int], float] = {}
    for j in range(height):
        for i in range(width):
            hits = 0
            for sy in range(SUBSAMPLES):
                py = j + (sy + 0.5) / SUBSAMPLES
                along_y = (py - center_y) * step_y  # <= 0 до центра окружности (со стороны угла клетки - больше 0)
                for sx in range(SUBSAMPLES):
                    px = i + (sx + 0.5) / SUBSAMPLES
                    along_x = (px - center_x) * step_x
                    if along_x <= 0 and along_y <= 0:  # участок дуги
                        inside = abs(math.hypot(px - center_x, py - center_y) - radius) <= half
                    elif along_y > 0 >= along_x:  # прямой конец вертикальной линии
                        inside = abs(px - axis_x) <= half
                    elif along_x > 0 >= along_y:  # прямой конец горизонтальной линии
                        inside = abs(py - axis_y) <= half
                    else:
                        inside = False
                    hits += inside
            if hits:
                result[i, j] = hits / SUBSAMPLES**2
    return result
