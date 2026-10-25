"""
Линии рамок: тонкие, толстые и двойные рукава, сходящиеся в центре клетки.
"""

from termsnap.png.boxes.arc import draw_arc
from termsnap.png.boxes.arms import DOUBLE, HEAVY, THIN, Arms
from termsnap.png.boxes.tile import Tile

#: Половина расстояния между линиями двойной рамки: не меньше двух пикселей (чтобы между линиями оставался просвет
#: даже при самой тонкой линии), а при толстой линии - в 1.6 раза больше ее толщины.
_DOUBLE_MIN_OFFSET = 2.0
_DOUBLE_OFFSET_PER_LIGHT = 1.6


def heavy_width(light: int) -> int:
    """
    Толщина толстой линии при толщине тонкой ``light``: вдвое больше и еще пиксель, чтобы центр оставался посередине.
    """
    return light * 2 + 1


def double_offset(light: int) -> float:
    """
    Расстояние от оси до каждой из двух линий двойной рамки при толщине тонкой линии ``light``.
    """
    return max(_DOUBLE_MIN_OFFSET, light * _DOUBLE_OFFSET_PER_LIGHT)


def draw_lines(tile: Tile, arms: Arms) -> None:
    """
    Рисует символ рамки по его рукавам: скругленный угол - дугой, остальное - прямоугольниками от края клетки к
    центру.
    """
    if arms.arc and (arms.up or arms.down) and (arms.left or arms.right):
        draw_arc(tile, arms)
        return
    _draw_plain_arms(tile, arms)
    # двойной рукав - две параллельные линии; концы у центра зависят от соседних рукавов, чтобы линии смыкались
    _draw_double_vertical(tile, arms, -1, arms.up, arms.down)
    _draw_double_vertical(tile, arms, 1, arms.down, arms.up)
    _draw_double_horizontal(tile, arms, -1, arms.left, arms.right)
    _draw_double_horizontal(tile, arms, 1, arms.right, arms.left)


#: Рукава: название, направление от центра (-1 - вверх или влево, 1 - вниз или вправо), вертикальный ли и название
#: противоположного рукава.
_ARMS = (("up", -1, True, "down"), ("down", 1, True, "up"), ("left", -1, False, "right"), ("right", 1, False, "left"))


def _draw_plain_arms(tile: Tile, arms: Arms) -> None:
    """
    Тонкие и толстые рукава: прямоугольник от края клетки через центр до противоположной стороны линии. Если рукав
    один на своей оси, а поперек идут двойные линии (``╒``, ``╓``, ``╤``, ``╟``), он продолжается до них:

        двойные рукава поперек с обеих сторон -> до ближней из двух линий (``╤``: вертикаль упирается в нижнюю линию)
        двойной рукав поперек с одной стороны -> до дальней линии (``╒``: вертикаль доходит до верхней, угол замкнут)
        иначе                                  -> до центра
    """
    cx, cy = tile.center_x, tile.center_y
    offset = double_offset(tile.light)
    edges = {"up": tile.top, "down": tile.bottom, "left": tile.left, "right": tile.right}
    for name, direction, vertical, opposite in _ARMS:
        weight = getattr(arms, name)
        if weight not in {THIN, HEAVY}:
            continue
        t = tile.light if weight == THIN else heavy_width(tile.light)
        centre = cy if vertical else cx
        end = centre - direction * t / 2  # за центр на полтолщины: линия перекрывает перпендикулярную
        crossing = (arms.left, arms.right) if vertical else (arms.up, arms.down)
        doubles = sum(other == DOUBLE for other in crossing)
        if doubles and not getattr(arms, opposite):
            reach = offset if doubles == 2 else -offset
            end = centre + direction * reach - direction * tile.light / 2
        if vertical:
            tile.fill(cx - t / 2, edges[name], cx + t / 2, end)
        else:
            tile.fill(edges[name], cy - t / 2, end, cy + t / 2)


def _double_end(centre: float, direction: int, offset: float, beside: int, across: int, opposite: int) -> float:
    """
    Где у центра кончается линия двойного рукава (``direction`` - куда он идет от центра). ``beside`` - рукав поперек
    с той же стороны от оси, что и линия, ``across`` - с другой, ``opposite`` - продолжение рукава за центром.

        рядом двойной рукав            -> до его ближней линии (внутренний угол: линии смыкаются)
        рядом тонкий или толстый рукав -> до его оси (он лежит по центру между линиями, линия к нему примыкает)
        только с другой стороны двойной, а продолжения нет -> до дальней линии (внешний угол замкнут)
        иначе                          -> до центра
    """
    if beside == DOUBLE:
        return centre + direction * offset
    if beside:
        return centre
    if across == DOUBLE and opposite != DOUBLE:
        return centre - direction * offset
    return centre


def _draw_double_vertical(tile: Tile, arms: Arms, direction: int, weight: int, opposite: int) -> None:
    """
    Двойной рукав вверх (``direction=-1``) или вниз (``1``): две вертикальные линии по сторонам от оси; концы у
    центра - см. ``_double_end``.
    """
    if weight != DOUBLE:
        return
    cx, cy, light, offset = tile.center_x, tile.center_y, tile.light, double_offset(tile.light)
    for side in (-1, 1):
        beside, across = (arms.left, arms.right) if side == -1 else (arms.right, arms.left)
        end = _double_end(cy, direction, offset, beside, across, opposite)
        edge = tile.top if direction < 0 else tile.bottom
        x = cx + side * offset
        tile.fill(x - light / 2, edge, x + light / 2, end - direction * light / 2)


def _draw_double_horizontal(tile: Tile, arms: Arms, direction: int, weight: int, opposite: int) -> None:
    """
    То же для двойного рукава влево (``direction=-1``) или вправо (``1``); см. ``_draw_double_vertical``.
    """
    if weight != DOUBLE:
        return
    cx, cy, light, offset = tile.center_x, tile.center_y, tile.light, double_offset(tile.light)
    for side in (-1, 1):
        beside, across = (arms.up, arms.down) if side == -1 else (arms.down, arms.up)
        end = _double_end(cx, direction, offset, beside, across, opposite)
        edge = tile.left if direction < 0 else tile.right
        y = cy + side * offset
        tile.fill(edge, y - light / 2, end - direction * light / 2, y + light / 2)
